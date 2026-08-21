"""
Планировщик одновременных запусков (admission control по ресурсам пода).

Модель:
- Потолок мощностей = лимиты пода (cgroup v2/v1, env POD_CPU_LIMIT / POD_MEM_GB_LIMIT
  или значения по умолчанию). Лимит пода — это жёсткий потолок: CPU троттлится,
  память уходит в OOM, поэтому проверка по памяти критична, по CPU — рекомендательна.
- Каждый тип задачи (точка) имеет вес (CPU ядер + ГБ памяти) и гарантированный
  минимум одновременных слотов (по умолчанию 1 — «точка запускается минимум 1 раз»).
- Перед КАЖДЫМ запуском проверяется, влезает ли ещё один запуск этого типа:
  первый слот каждого типа свободен всегда, последующие — только если
  нагрузка + вес нового запуска не превышают лимиты.

Если в нодах уже работают другие проекты — это не меняет модель: контейнер
не может выйти за свои limits, а гарантии по resources.requests обеспечивает
kube-scheduler. Для учёта свободных ресурсов всей ноды нужен доступ к API k8s
(RBAC) — при необходимости добавляется отдельно.
"""
import asyncio
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger('scheduler')


def _env_float(name, default):
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return float(default)


def _env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return int(default)


# --- Лимиты пода -----------------------------------------------------------


def _cgroup_v2_cpu_limit():
    try:
        with open('/sys/fs/cgroup/cpu.max') as f:
            quota, period = f.read().split()
        if quota == 'max':
            return None
        return int(quota) / int(period)
    except Exception:
        return None


def _cgroup_v2_mem_limit_gb():
    try:
        with open('/sys/fs/cgroup/memory.max') as f:
            value = f.read().strip()
        if value == 'max':
            return None
        return int(value) / (1024 ** 3)
    except Exception:
        return None


def _cgroup_v1_cpu_limit():
    for path in ('/sys/fs/cgroup/cpu/cpu.cfs_quota_us', '/sys/fs/cgroup/cpu,cpuacct/cpu.cfs_quota_us'):
        try:
            with open(path) as f:
                quota = int(f.read().strip())
            with open(path.replace('cpu.cfs_quota_us', 'cpu.cfs_period_us')) as f:
                period = int(f.read().strip())
            if quota <= 0 or period <= 0:
                return None
            return quota / period
        except Exception:
            continue
    return None


def _cgroup_v1_mem_limit_gb():
    for path in ('/sys/fs/cgroup/memory/memory.limit_in_bytes', '/sys/fs/cgroup/memory,cpuacct/memory.limit_in_bytes'):
        try:
            with open(path) as f:
                value = int(f.read().strip())
            if value <= 0 or value >= 2 ** 63:
                return None
            return value / (1024 ** 3)
        except Exception:
            continue
    return None


def get_cpu_limit() -> float:
    """Потолок CPU пода в ядрах."""
    env_v = os.environ.get('POD_CPU_LIMIT')
    if env_v:
        try:
            return float(env_v)
        except ValueError:
            pass
    return _cgroup_v2_cpu_limit() or _cgroup_v1_cpu_limit() or 2.0


def get_mem_limit_gb() -> float:
    """Потолок памяти пода в ГБ."""
    env_v = os.environ.get('POD_MEM_GB_LIMIT')
    if env_v:
        try:
            return float(env_v)
        except ValueError:
            pass
    return _cgroup_v2_mem_limit_gb() or _cgroup_v1_mem_limit_gb() or 4.0


# --- Веса задач ------------------------------------------------------------


@dataclass
class TaskWeight:
    cpu: float        # ядер CPU на один запуск
    mem_gb: float     # ГБ памяти на один запуск
    min_slots: int = 1  # гарантированный минимум одновременных запусков точки


def make_scheduler():
    """Собирает планировщик из env (веса настраиваются в ConfigMap)."""
    return Scheduler(
        weights={
            # /run: multi_pars + review_analysis x2 (браузеры открываются по очереди)
            'run': TaskWeight(
                cpu=_env_float('TASK_CPU_RUN', 1.0),
                mem_gb=_env_float('TASK_MEM_RUN', 1.5),
                min_slots=_env_int('TASK_MIN_SLOTS_RUN', 1),
            ),
            # /get_feedback: один playwright-браузер
            'get_feedback': TaskWeight(
                cpu=_env_float('TASK_CPU_GET_FEEDBACK', 0.7),
                mem_gb=_env_float('TASK_MEM_GET_FEEDBACK', 1.0),
                min_slots=_env_int('TASK_MIN_SLOTS_GET_FEEDBACK', 1),
            ),
        },
        base_cpu=_env_float('BASE_CPU', 0.3),        # сам uvicorn-сервис
        base_mem_gb=_env_float('BASE_MEM_GB', 0.5),
    )


class Scheduler:
    """Admission control: перед каждым запуском проверяет свободные мощности."""

    def __init__(self, weights: dict[str, TaskWeight], base_cpu: float, base_mem_gb: float):
        self.weights = weights
        self.base_cpu = base_cpu
        self.base_mem_gb = base_mem_gb
        self._lock = asyncio.Lock()
        self._running = {t: 0 for t in weights}

    def _load(self):
        cpu = self.base_cpu
        mem = self.base_mem_gb
        for t, w in self.weights.items():
            cpu += self._running[t] * w.cpu
            mem += self._running[t] * w.mem_gb
        return cpu, mem

    async def try_acquire(self, task_type: str) -> tuple[bool, str]:
        """Пытается занять слот под новый запуск. Возвращает (ok, сообщение)."""
        w = self.weights.get(task_type)
        if w is None:
            return False, f'Неизвестный тип задачи: {task_type}'

        async with self._lock:
            # Гарантированный минимум: первая задача каждого типа запускается всегда
            if self._running[task_type] < w.min_slots:
                self._running[task_type] += 1
                return True, 'ok: гарантированный слот'

            cpu, mem = self._load()
            cpu_limit = get_cpu_limit()
            mem_limit = get_mem_limit_gb()

            if mem + w.mem_gb > mem_limit:
                return False, (
                    f'Недостаточно памяти: занято {mem:.1f} ГБ из {mem_limit:.1f} ГБ, '
                    f'запуск {task_type!r} требует ещё {w.mem_gb:.1f} ГБ'
                )

            if cpu + w.cpu > cpu_limit:
                return False, (
                    f'Недостаточно CPU: занято {cpu:.1f} из {cpu_limit:.1f} ядер, '
                    f'запуск {task_type!r} требует ещё {w.cpu:.1f}'
                )

            self._running[task_type] += 1
            return True, 'ok: есть свободные мощности'

    async def release(self, task_type: str):
        async with self._lock:
            if self._running.get(task_type, 0) > 0:
                self._running[task_type] -= 1

    def _capacity_for(self, task_type: str) -> dict:
        """Сколько ещё запусков этого типа влезет по каждому ресурсу."""
        w = self.weights[task_type]
        cpu, mem = self._load()
        cpu_limit = get_cpu_limit()
        mem_limit = get_mem_limit_gb()
        by_cpu = max(0, int((cpu_limit - cpu) // w.cpu))
        by_mem = max(0, int((mem_limit - mem) // w.mem_gb))
        return {'by_cpu': by_cpu, 'by_mem': by_mem, 'min': min(by_cpu, by_mem)}

    def snapshot(self) -> dict:
        """Текущее состояние мощностей — для точки /capacity."""
        cpu, mem = self._load()
        cpu_limit = get_cpu_limit()
        mem_limit = get_mem_limit_gb()
        return {
            'cpu_limit': cpu_limit,
            'mem_limit_gb': mem_limit,
            'base_cpu': self.base_cpu,
            'base_mem_gb': self.base_mem_gb,
            'running': dict(self._running),
            'load_cpu': cpu,
            'load_mem_gb': mem,
            'free_cpu': max(0.0, cpu_limit - cpu),
            'free_mem_gb': max(0.0, mem_limit - mem),
            'capacity_more': {t: self._capacity_for(t) for t in self.weights},
        }
