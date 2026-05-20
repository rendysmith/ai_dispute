import asyncio
import os
import time
from datetime import datetime, timedelta
from os.path import join, dirname
import locale
from typing import Optional, Dict, Any, List

import httpx
import pandas as pd
from dotenv import load_dotenv


from urllib.parse import urlparse, urlunparse


from utils.gs_editor import get_service, read_table_id, append_data_to_sheet_cell, append_data_to_sheet_scopes, \
    append_data_to_sheet_scope

# Устанавливаем русскую локаль для корректного перевода месяцев
# Для Linux/macOS часто используется 'ru_RU.UTF-8'
# Для Windows обычно достаточно 'ru_RU' или 'Russian'
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

#http://176.124.192.108:8000/swagger#/Geo/geo_analysis_api_v1_data_geo_analysis_post

async def rename_keys(data: dict) -> dict:
    mapping = {
        'date': 'Дата отзыва',
        'author': 'Автор отзыва',
        'feedback': 'Текст отзыва',
        'rating': 'Оценка'
    }

    return {mapping.get(key, key): value for key, value in data.items()}

async def extract_org_url_parse(url: str) -> str:
    """
    Извлечение с использованием urllib.parse.
    """
    parsed = urlparse(url)
    # Разделяем путь и берем часть до /reviews
    path_parts = parsed.path.split('/reviews')[0]

    # Собираем URL обратно без query параметров
    clean_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        path_parts,
        '',  # params
        '',  # query
        ''  # fragment
    ))
    return clean_url

async def transform_items(items: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
    """
    Трансформирует список словарей в словарь, где ключи - это ключи из словарей,
    а значения - списки всех значений по этим ключам.

    Пример:
    Вход: [{'date': '21.04.2026', 'rating': 5}, {'date': '14.05.2026', 'rating': 4}]
    Выход: {'date': ['21.04.2026', '14.05.2026'], 'rating': [5, 4]}
    """
    if not items:
        return {}

    # Получаем все уникальные ключи из первого словаря
    # (предполагаем, что структура одинаковая)
    keys = items[0].keys()

    # Создаем словарь с пустыми списками для каждого ключа
    result = {key: [] for key in keys}

    # Заполняем списки значениями
    for item in items:
        for key in keys:
            result[key].append(item.get(key))

    return result

class GetBlock:
    def __init__(self, base_url: str = "http://176.124.192.108:8000"):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(base_url=self.base_url,
                                        timeout=httpx.Timeout(120.0, connect=10.0))
        self.headers = {
        "accept": "application/json"
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def create_task(self, link: str, topic: Optional[str] = None) -> Dict[str, Any]:
        """
        1. POST /api/v1/data/get_feedbacks
        Точка для сбора отзывов о компании. Регистрирует задачу в общей очереди.
        """
        url = f"{self.base_url}/api/v1/data/get_feedbacks"
        print(url)
        params = {"link": link, "topic": topic}

        response = await self.client.post(url,
                                          headers=self.headers,
                                          params=params,
                                          auth=(username, password))
        response.raise_for_status()
        return response.json()

    async def get_task_status(self, task_key: str) -> Dict[str, Any]:
        """
        2. GET /api/v1/data/reviews_task_status
        Проверить статус выполнения задачи парсинга.
        """
        url = "/api/v1/data/reviews_task_status"
        params = {"task_key": task_key}

        response = await self.client.get(url,
                                        headers=self.headers,
                                        params=params,
                                        auth=(username, password))
        response.raise_for_status()
        return response.json()

    async def stop_task(self, task_key: str) -> Dict[str, Any]:
        """
        3. POST /api/v1/data/stop_parsing_task
        Остановить активную задачу парсинга.
        """
        url = "/api/v1/data/stop_parsing_task"
        params = {"task_key": task_key}

        response = await self.client.post(url,
                                          headers=self.headers,
                                          params=params,
                                          auth=(username, password))
        response.raise_for_status()
        return response.json()

    async def cancel_task(self, task_key: str) -> Dict[str, Any]:
        """
        4. POST /api/v1/data/cancel_reviews_task
        Отменить задачу парсинга отзывов.
        """
        url = "/api/v1/data/cancel_reviews_task"
        params = {"task_key": task_key}

        response = await self.client.post(url,
                                          headers=self.headers,
                                          params=params,
                                          auth=(username, password))
        response.raise_for_status()
        return response.json()

    async def get_parsing_queue(self) -> Dict[str, Any]:
        """
        5. GET /api/v1/data/parsing_queue
        Возвращает собранные blocks синхронно.
        """
        url = "/api/v1/data/parsing_queue"

        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Закрыть асинхронную HTTP-сессию."""
        await self.client.aclose()

async def main_automir():
    # Инициализируем сервис Google Sheets
    service = await get_service()

    tab = 'Яндекс карты'
    df_cards = await read_table_id(service, ss_id_cards, tab)
    print(df_cards)

    try:
        df_links = await read_table_id(service, ss_id_feedback, formatted_month_year)
        links = df_links['Ссылка'].to_list()
        feedbacks = df_links['Текст отзыва'].to_list()
    except:
        links = []
        feedbacks = []

    existing_pairs = set(zip(links, feedbacks))
    # Используем асинхронный контекстный менеджер.
    # Клиент откроется перед циклом и корректно закроется сам после его завершения.
    async with GetBlock() as client:
        for idx, row in df_cards.iterrows():
            city = row['ГОРОД']
            brand = row['МАРКА']
            link_orig = row['ССЫЛКА']
            #address = row['address']
            date = row['date']

            # Пропускаем строку, если дата совпадает
            if date == today_str:
                continue

            link = await extract_org_url_parse(link_orig)
            print(f'{idx} {link}')

            # Проверяем ссылку на NaN (бывает при чтении из таблиц)
            if not isinstance(link, str) or not link.startswith('http'):
                print(f"[{idx}] Пропуск: неверный формат ссылки: {link}")
                continue

            # Генерируем УНИКАЛЬНЫЙ ключ для каждой строки внутри цикла
            my_task_key = f"task_{int(time.time())}_{idx}"

            try:
                print(f"\n[{idx}] Запуск задачи для {brand} ({city})...")
                start_res = await client.create_task(link=link, topic=my_task_key)
                print("Ответ сервера:", start_res)

                # 2. Проверка статуса
                print("Проверка статуса задачи...")
                status_res = await client.get_task_status(task_key=my_task_key)
                print("Статус:", status_res)

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

                print(datas.keys())

                del datas['review_link']
                print(datas)

                df_datas = pd.DataFrame(datas)
                print(df_datas)

                # Перебор строк DataFrame как словарей
                for _, row in df_datas.iterrows():
                    row_dict = row.to_dict()

                    date = row_dict['Дата отзыва']

                    if date != today_str and date != yesterday_str:
                        continue

                    text = row_dict['Текст отзыва']
                    old_link = row_dict['Ссылка']

                    # Проверяем пару (ссылка, текст)
                    if (old_link, text) in existing_pairs:
                        print(f'\n> Запись уже есть в таблице: {text}')
                        continue

                    await append_data_to_sheet_scope(service, ss_id_feedback, formatted_month_year, row_dict)
                    await asyncio.sleep(3)
                    # Добавляем новую пару в множество, чтобы не задвоить в текущем цикле
                    existing_pairs.add((old_link, text))

                await append_data_to_sheet_cell(service, ss_id_cards, tab, 'date', idx + 2, today_str)
                df_cards.at[idx, 'date'] = today_str
                #await append_data_to_sheet_scopes(service, ss_id_feedback, formatted_month_year, datas)

            except httpx.HTTPStatusError as exc:
                print(f"- ERROR Ошибка HTTP на строке {idx}: {exc.response.status_code} - {exc.response.text}")

            except Exception as exc:
                print(f"- ERROR Произошла ошибка на строке {idx}: {exc}")


        # datas = await get_blocks(link)
        # print(datas)
        #
        # if datas['items'] == []:
        #     pass
        #
        # else:
        #     print('Переименовать колонки, записать в таблицу')
        #     #await append_data_to_sheet_scopes(service, ss_id_feedback, formatted_month_year, datas)
        #
        # await append_data_to_sheet_cell(service, ss_id_cards, tab, 'date', idx + 2, today_str)

async def tst_create_task():
    """Тестовая функция для проверки create_task"""
    async with GetBlock() as gb:
        url = 'https://yandex.ru/maps/org/1157214158'
        datas = await gb.create_task(url, "test_task_001")
        print(datas)

        return datas

if __name__ ==  "__main__":
    asyncio.run(main_automir())


