"""
Launcher для Automir: считает свободные worker-ноды и создаёт Indexed Job с N воркерами.

Запускается из CronJob ai-automir-launcher (in-cluster ServiceAccount + RBAC).
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from kubernetes import client, config
from kubernetes.client.rest import ApiException

MEMORY_UNITS = {
    "Ki": 1024,
    "Mi": 1024**2,
    "Gi": 1024**3,
    "Ti": 1024**4,
}


def parse_memory(value: str) -> int:
    """K8s quantity → bytes."""
    if not value:
        return 0
    value = str(value).strip()
    for suffix, mult in MEMORY_UNITS.items():
        if value.endswith(suffix):
            return int(float(value[: -len(suffix)]) * mult)
    return int(value)


def parse_cpu(value: str) -> int:
    """K8s quantity → millicores."""
    if not value:
        return 0
    value = str(value).strip()
    if value.endswith("m"):
        return int(value[:-1])
    return int(float(value) * 1000)


def format_memory(bytes_val: int) -> str:
    if bytes_val >= MEMORY_UNITS["Gi"]:
        return f"{bytes_val / MEMORY_UNITS['Gi']:.0f}Gi"
    if bytes_val >= MEMORY_UNITS["Mi"]:
        return f"{bytes_val / MEMORY_UNITS['Mi']:.0f}Mi"
    return str(bytes_val)


def is_control_plane(node: client.V1Node) -> bool:
    labels = node.metadata.labels or {}
    for key in ("node-role.kubernetes.io/control-plane", "node-role.kubernetes.io/master"):
        if key in labels:
            return True
    return False


def is_node_ready(node: client.V1Node) -> bool:
    for cond in node.status.conditions or []:
        if cond.type == "Ready" and cond.status == "True":
            return True
    return False


def pod_requests(pod: client.V1Pod) -> Tuple[int, int]:
    mem = cpu = 0
    if not pod.spec or not pod.spec.containers:
        return mem, cpu
    for container in pod.spec.containers:
        req = container.resources.requests if container.resources else None
        if not req:
            continue
        if req.get("memory"):
            mem += parse_memory(req["memory"])
        if req.get("cpu"):
            cpu += parse_cpu(req["cpu"])
    return mem, cpu


def requests_by_node(v1: client.CoreV1Api) -> Dict[str, Tuple[int, int]]:
    totals: Dict[str, Tuple[int, int]] = {}
    pods = v1.list_pod_for_all_namespaces(
        field_selector="status.phase!=Succeeded,status.phase!=Failed"
    )
    for pod in pods.items:
        node_name = pod.spec.node_name if pod.spec else None
        if not node_name:
            continue
        mem, cpu = pod_requests(pod)
        cur_mem, cur_cpu = totals.get(node_name, (0, 0))
        totals[node_name] = (cur_mem + mem, cur_cpu + cpu)
    return totals


def eligible_worker_nodes(
    v1: client.CoreV1Api,
    *,
    min_free_memory: int,
    min_free_cpu: int,
) -> List[client.V1Node]:
    used = requests_by_node(v1)
    eligible: List[client.V1Node] = []

    for node in v1.list_node().items:
        name = node.metadata.name
        if node.spec and node.spec.unschedulable:
            print(f"skip {name}: cordoned/unschedulable")
            continue
        if is_control_plane(node):
            print(f"skip {name}: control-plane")
            continue
        if not is_node_ready(node):
            print(f"skip {name}: not Ready")
            continue

        alloc = node.status.allocatable or {}
        alloc_mem = parse_memory(alloc.get("memory", "0"))
        alloc_cpu = parse_cpu(alloc.get("cpu", "0"))
        used_mem, used_cpu = used.get(name, (0, 0))
        free_mem = alloc_mem - used_mem
        free_cpu = alloc_cpu - used_cpu

        print(
            f"node {name}: free_mem={format_memory(free_mem)} "
            f"free_cpu={free_cpu}m (need mem>={format_memory(min_free_memory)}, cpu>={min_free_cpu}m)"
        )

        if free_mem >= min_free_memory and free_cpu >= min_free_cpu:
            eligible.append(node)

    eligible.sort(key=lambda n: n.metadata.name)
    return eligible


def active_automir_jobs(batch_v1: client.BatchV1Api, namespace: str) -> List[client.V1Job]:
    jobs = batch_v1.list_namespaced_job(
        namespace=namespace,
        label_selector="app=ai-automir-workers",
    )
    active: List[client.V1Job] = []
    for job in jobs.items:
        status = job.status
        if not status:
            active.append(job)
            continue
        if (status.active or 0) > 0:
            active.append(job)
            continue
        if status.succeeded is None and status.failed is None:
            active.append(job)
    return active


def configure_kube_client_incluster_strict() -> None:
    """
    Надёжная настройка клиента в кластере.

    В некоторых кластерах `config.load_incluster_config()` завершается без ошибки,
    но реальные запросы уходят без Bearer-токена → API отвечает как system:anonymous.
    Здесь мы читаем токен/CA напрямую и явно задаём Authorization header.
    """
    token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
    ca_path = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
    host = os.environ.get("KUBERNETES_SERVICE_HOST")
    port = os.environ.get("KUBERNETES_SERVICE_PORT", "443")
    if not host:
        raise RuntimeError("KUBERNETES_SERVICE_HOST is not set")

    try:
        with open(token_path, "r", encoding="utf-8") as f:
            token = f.read().strip()
    except OSError as exc:
        raise RuntimeError(f"Cannot read serviceaccount token at {token_path}: {exc}") from exc

    if not token:
        raise RuntimeError(f"Serviceaccount token at {token_path} is empty")

    cfg = client.Configuration.get_default_copy()
    cfg.host = f"https://{host}:{port}"
    cfg.ssl_ca_cert = ca_path if os.path.exists(ca_path) else None
    cfg.verify_ssl = True

    # Python client expects `api_key['authorization'] = 'Bearer ...'`
    cfg.api_key = {"authorization": f"Bearer {token}"}
    client.Configuration.set_default(cfg)


def build_worker_job(
    *,
    name: str,
    namespace: str,
    image: str,
    workers: int,
    memory_request: str,
    memory_limit: str,
    cpu_request: str,
    cpu_limit: str,
    secret_name: str,
    image_pull_secret: str,
) -> client.V1Job:
    worker_script = """
echo "Automir worker index: $JOB_COMPLETION_INDEX / $TOTAL_WORKERS"
set -e
timeout 7200s python3 -u -c "
import asyncio, sys, traceback
try:
    from products.automir import main_automir
    asyncio.run(main_automir())
except Exception:
    traceback.print_exc()
    sys.stdout.flush()
    sys.stderr.flush()
    raise SystemExit(1)
"
""".strip()

    container = client.V1Container(
        name="automir",
        image=image,
        image_pull_policy="Always",
        env_from=[client.V1EnvFromSource(secret_ref=client.V1SecretEnvSource(name=secret_name))],
        env=[
            client.V1EnvVar(
                name="JOB_COMPLETION_INDEX",
                value_from=client.V1EnvVarSource(
                    field_ref=client.V1ObjectFieldSelector(
                        field_path="metadata.annotations['batch.kubernetes.io/job-completion-index']"
                    )
                ),
            ),
            client.V1EnvVar(name="TOTAL_WORKERS", value=str(workers)),
        ],
        command=["/bin/sh", "-c"],
        args=[worker_script],
        resources=client.V1ResourceRequirements(
            requests={"memory": memory_request, "cpu": cpu_request},
            limits={"memory": memory_limit, "cpu": cpu_limit},
        ),
    )

    pod_spec = client.V1PodSpec(
        restart_policy="Never",
        service_account_name=None,
        image_pull_secrets=[client.V1LocalObjectReference(name=image_pull_secret)],
        affinity=client.V1Affinity(
            pod_anti_affinity=client.V1PodAntiAffinity(
                preferred_during_scheduling_ignored_during_execution=[
                    client.V1WeightedPodAffinityTerm(
                        weight=100,
                        pod_affinity_term=client.V1PodAffinityTerm(
                            label_selector=client.V1LabelSelector(
                                match_labels={"app": "ai-automir-workers"}
                            ),
                            topology_key="kubernetes.io/hostname",
                        ),
                    )
                ]
            )
        ),
        containers=[container],
    )

    return client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(
            name=name,
            namespace=namespace,
            labels={
                "app": "ai-automir-workers",
                "launched-by": "ai-automir-launcher",
            },
        ),
        spec=client.V1JobSpec(
            completions=workers,
            parallelism=workers,
            completion_mode="Indexed",
            backoff_limit_per_index=2,
            backoff_limit=max(workers * 2, 8),
            ttl_seconds_after_finished=86400,
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "ai-automir-workers"}),
                spec=pod_spec,
            ),
        ),
    )


def main() -> int:
    namespace = os.environ.get("KUBERNETES_NAMESPACE", "default")
    max_workers = int(os.environ.get("AUTOMIR_MAX_WORKERS", "4"))
    min_workers = int(os.environ.get("AUTOMIR_MIN_WORKERS", "1"))
    schedule_memory = os.environ.get("AUTOMIR_SCHEDULE_MEMORY", "3Gi")
    schedule_cpu = os.environ.get("AUTOMIR_SCHEDULE_CPU", "500m")
    image = os.environ.get("AUTOMIR_IMAGE", "ghcr.io/rendysmith/ai_one_off:latest")
    secret_name = os.environ.get("AUTOMIR_SECRET_NAME", "products-env")
    image_pull_secret = os.environ.get("AUTOMIR_IMAGE_PULL_SECRET", "ghcr-secret")
    memory_request = os.environ.get("AUTOMIR_WORKER_MEMORY_REQUEST", "256Mi")
    memory_limit = os.environ.get("AUTOMIR_WORKER_MEMORY_LIMIT", "3Gi")
    cpu_request = os.environ.get("AUTOMIR_WORKER_CPU_REQUEST", "200m")
    cpu_limit = os.environ.get("AUTOMIR_WORKER_CPU_LIMIT", "1500m")

    min_free_mem = parse_memory(schedule_memory)
    min_free_cpu = parse_cpu(schedule_cpu)

    try:
        # 1) Пытаемся штатно
        config.load_incluster_config()
        # 2) И поверх — строгая настройка токена/CA
        configure_kube_client_incluster_strict()
        print("Loaded in-cluster kubeconfig (strict token auth)")
    except config.ConfigException:
        config.load_kube_config()
        print("Loaded local kubeconfig")

    v1 = client.CoreV1Api()
    batch_v1 = client.BatchV1Api()

    running = active_automir_jobs(batch_v1, namespace)
    if running:
        names = ", ".join(j.metadata.name for j in running)
        print(f"Automir Job уже выполняется ({names}), пропускаем запуск")
        return 0

    eligible = eligible_worker_nodes(
        v1,
        min_free_memory=min_free_mem,
        min_free_cpu=min_free_cpu,
    )
    workers = min(len(eligible), max_workers)

    print(f"Eligible nodes: {len(eligible)}, workers to launch: {workers}")

    if workers < min_workers:
        print(
            f"Недостаточно свободных нод ({workers} < {min_workers}). "
            "Пропускаем — следующий cron попробует снова."
        )
        return 0

    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    job_name = f"automir-run-{ts}"
    if len(job_name) > 63:
        job_name = job_name[:63].rstrip("-")

    job = build_worker_job(
        name=job_name,
        namespace=namespace,
        image=image,
        workers=workers,
        memory_request=memory_request,
        memory_limit=memory_limit,
        cpu_request=cpu_request,
        cpu_limit=cpu_limit,
        secret_name=secret_name,
        image_pull_secret=image_pull_secret,
    )

    try:
        batch_v1.create_namespaced_job(namespace=namespace, body=job)
    except ApiException as exc:
        print(f"Не удалось создать Job {job_name}: {exc}")
        return 1

    print(f"Created Job {job_name} with {workers} worker(s), TOTAL_WORKERS={workers}")
    for node in eligible[:workers]:
        print(f"  expected slot on: {node.metadata.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
