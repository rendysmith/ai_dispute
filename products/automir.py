import asyncio
import logging
import os
import time
import traceback
from datetime import datetime, timedelta
from os.path import join, dirname
import locale
from typing import Optional, Dict, Any, List

import httpx
import pandas as pd
from dotenv import load_dotenv
from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException

from urllib.parse import urlparse, urlunparse

from utils.gs_editor import get_service, read_table_id, append_data_to_sheet_cell, append_data_to_sheet_scopes, \
    append_data_to_sheet_scope

logger = logging.getLogger(__name__)

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


class GetBlock:
    def __init__(self, base_url: str = "http://176.124.192.108:8000"):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(120.0, connect=10.0)
        )
        self.headers = {"accept": "application/json"}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def create_task(self, link: str, topic: Optional[str] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/data/get_feedbacks"
        params = {"link": link, "topic": topic}
        response = await self.client.post(url, headers=self.headers, params=params, auth=(username, password))
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

    async def get_parsing_queue(self) -> Dict[str, Any]:
        url = "/api/v1/data/parsing_queue"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

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

            my_task_key = f"task_{int(time.time())}_{idx}"

            try:
                print(f"\n[{idx}] Запуск задачи для {brand} ({city})...")
                start_res = await client.create_task(link=link, topic=my_task_key)
                print("Ответ сервера:", start_res)

                print("Проверка статуса задачи...")
                status_res = await client.get_task_status(task_key=my_task_key)
                print("Статус:", status_res['detail'])

                datas = start_res['items']
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

                # Перебор строк DataFrame как словарей
                for _, data_row in df_datas.iterrows():
                    row_dict = data_row.to_dict()
                    date_review = row_dict.get('Дата отзыва', '')

                    if date_review != today_str and date_review != yesterday_str:
                        continue

                    text = row_dict.get('Текст отзыва', '')
                    old_link = row_dict.get('Ссылка', '')

                    # Проверяем пару (ссылка, текст)
                    if (old_link, text) in existing_pairs:
                        print(f'\n> Запись уже есть в таблице: {text}')
                        continue

                    await append_data_to_sheet_scope(service, ss_id_feedback, formatted_month_year, row_dict)
                    await asyncio.sleep(3)
                    existing_pairs.add((old_link, text))

                await append_data_to_sheet_cell(service, ss_id_cards, tab, 'date', idx + 2, today_str)

            except httpx.HTTPStatusError as exc:
                print(f"- ERROR Ошибка HTTP на строке {idx}: {exc.response.status_code} - {exc.response.text}")

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