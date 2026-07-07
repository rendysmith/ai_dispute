import asyncio
import os
import traceback

from products.automir import main_automir
from products.sber_polis import main_sber_polis

# Список задач для k8s Indexed Job (completions = len(PRODUCT_TASKS) в deploy/products-cronjob.yaml)
PRODUCT_TASKS = [
    ("automir", main_automir),
    ("sber_polis", main_sber_polis),
]

PRODUCT_MAX_WORKERS = 2


def _is_k8s_job() -> bool:
    return (
        os.environ.get("JOB_COMPLETION_INDEX") is not None
        or os.path.exists("/var/run/secrets/kubernetes.io")
    )


async def run_product_task(index: int) -> None:
    if index >= len(PRODUCT_TASKS):
        print(f"--- Index {index}: нет задачи, выход")
        return

    name, task = PRODUCT_TASKS[index]
    print(f"--- Start product: {name} (index {index})")
    try:
        await task()
    except Exception:
        print(f"--- Error in {name} ---")
        traceback.print_exc()
        raise
    print(f"--- Done product: {name}")


async def main():
    product_task = os.environ.get("PRODUCT_TASK")
    if product_task:
        for name, task in PRODUCT_TASKS:
            if name == product_task:
                print(f"--- Start product: {name} (PRODUCT_TASK)")
                try:
                    await task()
                except Exception:
                    print(f"--- Error in {name} ---")
                    traceback.print_exc()
                    raise
                print(f"--- Done product: {name}")
                return
        raise SystemExit(
            f"Unknown PRODUCT_TASK: {product_task}. "
            f"Available: {[n for n, _ in PRODUCT_TASKS]}"
        )

    if _is_k8s_job():
        index = int(os.environ.get("JOB_COMPLETION_INDEX", 0))
        await run_product_task(index)
        return

    # Локальный запуск: последовательно, ошибка одной задачи не блокирует вторую
    for index, (name, _) in enumerate(PRODUCT_TASKS):
        try:
            await run_product_task(index)
        except Exception:
            print(f"--- Continue after error in {name} ---")


if __name__ == "__main__":
    asyncio.run(main())
