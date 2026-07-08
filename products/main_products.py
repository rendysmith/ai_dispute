"""
Локальный/ручной запуск продуктов.
В Kubernetes используются отдельные CronJob'ы:
  - deploy/automir-cronjob.yaml   → 4 воркера main_automir
  - deploy/sberpolis-cronjob.yaml → 1 воркер main_sber_polis

Не используйте этот файл как Indexed Job на 4+ pod'а:
здесь всего 2 задачи (automir, sber_polis), без шардинга automir.
"""
import asyncio
import os
import traceback

from products.automir import main_automir
from products.sber_polis import main_sber_polis

PRODUCT_TASKS = [
    ("automir", main_automir),
    ("sber_polis", main_sber_polis),
]


async def run_one(name: str, task) -> None:
    print(f"--- Start product: {name}")
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
                await run_one(name, task)
                return
        raise SystemExit(
            f"Unknown PRODUCT_TASK: {product_task}. "
            f"Available: {[n for n, _ in PRODUCT_TASKS]}"
        )

    # Локально: последовательно (ошибка одной задачи не блокирует вторую)
    for name, task in PRODUCT_TASKS:
        try:
            await run_one(name, task)
        except Exception:
            print(f"--- Continue after error in {name} ---")


if __name__ == "__main__":
    asyncio.run(main())
