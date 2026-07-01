import asyncio
import logging
import os
import re
import time
import traceback
from datetime import datetime, timedelta
from os.path import join, dirname
import locale
from typing import Optional, Dict, Any, List, Tuple

import httpx
import pandas as pd
from dotenv import load_dotenv

from urllib.parse import urlparse, urlunparse

from utils.gs_editor import get_service, read_table_id, append_data_to_sheet_cell, append_data_to_sheet_scopes, \
    append_data_to_sheet_scope

logger = logging.getLogger(__name__)

QUEUE_WAITING = 'waiting'
QUEUE_RUNNING = 'running'
QUEUE_COMPLETED = 'completed'
QUEUE_ERROR = 'error'
QUEUE_CANCELLED = 'cancelled'
QUEUE_STOPPED = 'stopped'
ACTIVE_STATUSES = {QUEUE_WAITING, QUEUE_RUNNING}
TERMINAL_FAILURE_STATUSES = {QUEUE_ERROR, QUEUE_CANCELLED, QUEUE_STOPPED}

# Устанавливаем русскую локаль для корректного перевода месяцев
try:
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_TIME, 'Russian')


# Получаем текущую дату и время
current_date = datetime.now()

# Форматируем в нужный вид (разделитель — точка)
today_str = current_date.strftime("%d.%m.%Y")
yesterday_str = (current_date - timedelta(days=1)).strftime("%d.%m.%Y")

months_ru = [
    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]

month_name = months_ru[current_date.month]
year = current_date.year
formatted_month_year = f"{month_name} {year}"

print(today_str)
print(formatted_month_year)

dotenv_path = join(dirname(dirname(__file__)), '.env')
load_dotenv(dotenv_path)

username = os.environ.get("HOST_USERNAME")
password = os.environ.get("HOST_PASSWORD")
parser_api_url = os.environ.get("PARSER_API_URL", "http://176.124.192.108:8000")
task_poll_interval = float(os.environ.get("TASK_POLL_INTERVAL", "10"))
task_timeout_sec = float(os.environ.get("TASK_TIMEOUT_SEC", "900"))
task_stale_sec = float(os.environ.get("TASK_STALE_SEC", "300"))
task_create_read_timeout = float(os.environ.get("TASK_CREATE_READ_TIMEOUT", "120"))

ss_id_cards = '163Wdetech2MkZEdzeaFrhvGgPq9hfo6yWpgXP1YWI6k'
ss_id_feedback = '1wBtEuU9tAYTDtI1CtDsipV9lcHMnC6ndN0WXKa_tzsg'


async def get_node_info():
    """
    Используем JOB_COMPLETION_INDEX если запущены как Job,
    иначе локальный режим.
    """
    worker_index = int(os.environ.get('JOB_COMPLETION_INDEX', 0))
    total_workers = int(os.environ.get('TOTAL_WORKERS', 1))
    node_name = f"worker-{worker_index}"

    logger.info(f"Worker index: {worker_index}/{total_workers}")
    return node_name, worker_index, total_workers

async def rename_keys(data: dict) -> dict:
    mapping = {
        'date': 'Дата отзыва',
        'author': 'Автор отзыва',
        'feedback': 'Текст отзыва',
        'rating': 'Оценка'
    }
    return {mapping.get(key, key): value for key, value in data.items()}


async def extract_org_url_parse(url: str) -> str:
    parsed = urlparse(url)
    path_parts = parsed.path.split('/reviews')[0]
    clean_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        path_parts,
        '', '', ''
    ))
    return clean_url


async def transform_items(items: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
    if not items:
        return {}
    keys = items[0].keys()
    result = {key: [] for key in keys}
    for item in items:
        for key in keys:
            result[key].append(item.get(key))
    return result


def task_key_for_link(link: str, row_idx: int) -> str:
    org_match = re.search(r'/org/(\d+)', link)
    if org_match:
        return f"task_automir_{org_match.group(1)}_{row_idx}"
    return f"task_automir_{abs(hash(link))}_{row_idx}"


def items_from_blocks(blocks: Any) -> List[Dict[str, Any]]:
    if not isinstance(blocks, dict):
        return []
    items = blocks.get('items')
    return items if isinstance(items, list) else []


def is_sync_blocks_response(response: Dict[str, Any]) -> bool:
    return isinstance(response, dict) and 'items' in response and 'status' not in response


class GetBlock:
    def __init__(self, base_url: str = parser_api_url):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(120.0, connect=10.0),
        )
        self.headers = {"accept": "application/json"}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def create_task(self, link: str, topic: Optional[str] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/data/get_feedbacks"
        params = {"link": link, "topic": topic}
        response = await self.client.post(
            url,
            headers=self.headers,
            params=params,
            auth=(username, password),
            timeout=httpx.Timeout(task_create_read_timeout, connect=10.0),
        )
        response.raise_for_status()
        return response.json()

    async def get_task_status(self, task_key: str) -> Dict[str, Any]:
        url = "/api/v1/data/reviews_task_status"
        params = {"task_key": task_key}
        response = await self.client.get(url, headers=self.headers, params=params, auth=(username, password))
        response.raise_for_status()
        return response.json()

    async def stop_task(self, task_key: str) -> Dict[str, Any]:
        url = "/api/v1/data/stop_parsing_task"
        params = {"task_key": task_key}
        response = await self.client.post(url, headers=self.headers, params=params, auth=(username, password))
        response.raise_for_status()
        return response.json()

    async def cancel_task(self, task_key: str) -> Dict[str, Any]:
        url = "/api/v1/data/cancel_reviews_task"
        params = {"task_key": task_key}
        response = await self.client.post(url, headers=self.headers, params=params, auth=(username, password))
        response.raise_for_status()
        return response.json()

    async def terminate_task_by_name(self, task_key: str) -> Dict[str, Any]:
        """Прекратить выполнение задачи по имени (topic / task_key)."""
        for method in (self.stop_task, self.cancel_task):
            try:
                result = await method(task_key)
                logger.info("Task %s terminated via %s", task_key, method.__name__)
                return result
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "terminate_task_by_name %s via %s: %s %s",
                    task_key,
                    method.__name__,
                    exc.response.status_code,
                    exc.response.text[:200],
                )
        raise RuntimeError(f"Не удалось остановить задачу '{task_key}'")

    async def get_parsing_queue(self) -> Dict[str, Any]:
        url = "/api/v1/data/parsing_queue"
        response = await self.client.get(url, headers=self.headers, auth=(username, password))
        response.raise_for_status()
        return response.json()

    async def find_active_task_key_for_link(self, link: str, row_idx: int) -> Optional[str]:
        task_key = task_key_for_link(link, row_idx)
        try:
            status_res = await self.get_task_status(task_key)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise

        if status_res.get('status') in ACTIVE_STATUSES:
            return task_key
        return None

    async def wait_for_task(
        self,
        task_key: str,
        *,
        poll_interval: float = task_poll_interval,
        timeout_sec: float = task_timeout_sec,
        stale_sec: float = task_stale_sec,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Ожидание завершения задачи через reviews_task_status.
        При таймауте или отсутствии прогресса — terminate_task_by_name.
        """
        started_at = time.monotonic()
        last_progress_at = started_at
        last_snapshot = None

        while True:
            try:
                status_res = await self.get_task_status(task_key)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    elapsed = time.monotonic() - started_at
                    if elapsed >= timeout_sec:
                        raise TimeoutError(
                            f"Задача '{task_key}' не найдена за {elapsed:.0f}с"
                        ) from exc
                    print(f"Task {task_key}: not_found, ждём {poll_interval}s...")
                    await asyncio.sleep(poll_interval)
                    continue
                raise

            status = status_res.get('status', '')
            snapshot = (status, status_res.get('detail', ''))
            if snapshot != last_snapshot:
                last_progress_at = time.monotonic()
                last_snapshot = snapshot

            print(f"Task {task_key}: {status} — {status_res.get('detail', '')}")

            if status == QUEUE_COMPLETED:
                items = items_from_blocks(status_res.get('result'))
                return items, status_res

            if status in TERMINAL_FAILURE_STATUSES:
                raise RuntimeError(
                    f"Задача '{task_key}' завершилась со статусом {status}: "
                    f"{status_res.get('detail', '')}"
                )

            elapsed = time.monotonic() - started_at
            stale = time.monotonic() - last_progress_at
            if elapsed >= timeout_sec or stale >= stale_sec:
                print(
                    f"Task {task_key}: таймаут (elapsed={elapsed:.0f}s, "
                    f"stale={stale:.0f}s), останавливаем..."
                )
                try:
                    await self.terminate_task_by_name(task_key)
                except RuntimeError as exc:
                    logger.warning("%s", exc)
                raise TimeoutError(
                    f"Задача '{task_key}' не ответила вовремя "
                    f"(elapsed={elapsed:.0f}s, stale={stale:.0f}s)"
                )

            await asyncio.sleep(poll_interval)

    async def run_feedbacks_task(self, link: str, row_idx: int) -> List[Dict[str, Any]]:
        """
        Запуск сбора отзывов: не дублирует активную задачу, ждёт результат через status API.
        """
        task_key = task_key_for_link(link, row_idx)
        active_key = await self.find_active_task_key_for_link(link, row_idx)
        if active_key:
            print(f"Активная задача уже есть: {active_key}, ждём завершения...")
            items, _ = await self.wait_for_task(active_key)
            return items

        try:
            start_res = await self.create_task(link=link, topic=task_key)
            if is_sync_blocks_response(start_res):
                return items_from_blocks(start_res)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 409:
                print(f"Задача '{task_key}' уже выполняется на сервере, ждём...")
            else:
                raise
        except httpx.ReadTimeout:
            print(f"create_task timeout для '{task_key}', продолжаем опрос статуса...")

        items, _ = await self.wait_for_task(task_key)
        return items

    async def close(self):
        await self.client.aclose()


async def main_automir():
    # Получаем информацию о нодах
    node_name, node_index, total_nodes = await get_node_info()

    service = await get_service()
    tab = 'Яндекс карты'
    df_cards = await read_table_id(service, ss_id_cards, tab)

    try:
        df_links = await read_table_id(service, ss_id_feedback, formatted_month_year)
        links = df_links['Ссылка'].to_list()
        feedbacks = df_links['Текст отзыва'].to_list()
    except:
        links = []
        feedbacks = []

    existing_pairs = set(zip(links, feedbacks))

    async with GetBlock() as client:
        for idx, row in df_cards.iterrows():
            # Каждая нода берёт только свои строки
            if idx % total_nodes != node_index:
                continue

            city = row['ГОРОД']
            brand = row['МАРКА']
            link_orig = row['ССЫЛКА']
            date_rec = row.get('date', '')

            # Пропускаем уже обработанные сегодня
            if date_rec == today_str:
                continue

            link = await extract_org_url_parse(link_orig)
            print(f'[{idx}] Node {node_name} обрабатывает: {link}')

            # Проверяем ссылку
            if not isinstance(link, str) or not link.startswith('http'):
                print(f"[{idx}] Пропуск: неверный формат ссылки: {link}")
                continue

            try:
                print(f"\n[{idx}] Запуск задачи для {brand} ({city})...")
                datas = await client.run_feedbacks_task(link=link, row_idx=idx)
                len_d = len(datas)
                print("Len D = ", len_d)

                if len_d == 0:
                    await append_data_to_sheet_cell(service, ss_id_cards, tab, 'date', idx + 2, today_str)
                    continue

                datas_trans = await transform_items(datas)
                datas = await rename_keys(datas_trans)
                datas['Дата выгрузки'] = [today_str] * len_d
                datas['ДЦ'] = [city] * len_d
                datas['Марка'] = [brand] * len_d
                datas['Площадка'] = ['Яндекс Карты'] * len_d
                datas['Ссылка'] = [link_orig] * len_d

                if 'review_link' in datas:
                    del datas['review_link']
                print(datas)

                df_datas = pd.DataFrame(datas)

                for _, data_row in df_datas.iterrows():
                    row_dict = data_row.to_dict()
                    date_review = row_dict.get('Дата отзыва', '')

                    if date_review != today_str and date_review != yesterday_str:
                        continue

                    text = row_dict.get('Текст отзыва', '')
                    old_link = row_dict.get('Ссылка', '')

                    if (old_link, text) in existing_pairs:
                        print(f'\n> Запись уже есть в таблице: {text}')
                        continue

                    await append_data_to_sheet_scope(service, ss_id_feedback, formatted_month_year, row_dict)
                    await asyncio.sleep(3)
                    existing_pairs.add((old_link, text))

                await append_data_to_sheet_cell(service, ss_id_cards, tab, 'date', idx + 2, today_str)

            except httpx.HTTPStatusError as exc:
                print(f"- ERROR Ошибка HTTP на строке {idx}: {exc.response.status_code} - {exc.response.text}")

            except TimeoutError as exc:
                print(f"- ERROR Таймаут на строке {idx}: {exc}")

            except Exception as exc:
                print(f"- ERROR Произошла ошибка на строке {idx}: {exc}")
                traceback.print_exc()


async def tst_create_task():
    """Тестовая функция для проверки create_task"""
    async with GetBlock() as gb:
        url = 'https://yandex.ru/maps/org/1157214158'
        datas = await gb.create_task(url, "test_task_001")
        print(datas)
        return datas


if __name__ == "__main__":
    asyncio.run(main_automir())