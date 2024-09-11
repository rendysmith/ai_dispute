import asyncio
import random

from datetime import datetime, timedelta

import zlib
import base64

from utils.gs_editor import pars_url, get_service, append_data_to_sheet_scope
from utils.ai_module import generate_and_white
from utils.user_agent import get_playwright

import os
from dotenv import load_dotenv

current_date = datetime.now()

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

async def compress_string(input_string):
    # Сжимаем строку с помощью zlib
    compressed_data = zlib.compress(input_string.encode('utf-8'))
    # Кодируем сжатые данные в Base64 для удобства хранения и передачи
    compressed_base64 = base64.b64encode(compressed_data)
    return compressed_base64.decode('utf-8')

async def decompress_string(compressed_string):
    # Декодируем данные из Base64
    compressed_data = base64.b64decode(compressed_string.encode('utf-8'))
    # Распаковываем данные с помощью zlib
    decompressed_data = zlib.decompress(compressed_data)
    return decompressed_data.decode('utf-8')

async def convert_date(month):
    months = {
        'января': 1,
        'февраля': 2,
        "марта": 3,
        "апреля": 4,
        "мая": 5,
        "июня": 6,
        "июля": 7,
        "августа": 8,
        "сентября": 9,
        "октября": 10,
        "ноября": 11,
        "декабря": 12
    }
    return months[month]

async def check_2gis(service, url, pattern, criteria, ss_id, project):
    url_split = url.split('/')
    city_company = url_split[3]
    id_obj = url_split[5]
    top_url = f'https://2gis.ru/{city_company}/firm/{id_obj}'

    datas = {'project': project,
             'url': url,
             'top_url': top_url}

    await append_data_to_sheet_scope(service, ss_id, 'unique_url', datas)

    playwright, browser, page = await get_playwright(top_url)

    ts = random.randint(5, max_sec)
    print(f'Wait {ts} sec...')
    await asyncio.sleep(ts)

    links = await pars_url(service, ss_id, project)
    if not page:
        return "Сайт не вернул данные"

    blocks = await page.query_selector_all('div[class="_11gvyqv"]')
    print('Len =', len(blocks))

    for block in blocks:
        try:
            date_content = await block.query_selector('div[class="_4mwq3d"]')
            date = await date_content.inner_text()
            date_split = date.split(', ')[0].split(' ')
            date_split = [dt.replace(',', '') for dt in date_split]
            print(date_split)

        except AttributeError as AE:
            date_content = await block.query_selector('div[class="_139ll30"]')
            date = await date_content.inner_text()
            date_split = date.split(' ')
            date_split = [dt.replace(',', '') for dt in date_split]
            print(date_split)

        day = int(date_split[0])
        month = await convert_date(date_split[1])
        year = int(date_split[2])

        target_date = datetime(year, month, day)
        formatted_date = target_date.strftime("%d.%m.%Y")
        print(formatted_date)

        if (current_date - target_date) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней = {date}.')
            continue

        try:
            answer_content = block.query_selector('div[class="_sgs1pz"]')
            answer = answer_content.inner_text()
            print('Уже есть ответ на комментарий')
            continue

        except:
            pass

        author_content = await block.query_selector('span[class="_16s5yj36"]')
        author = await author_content.inner_text()
        author = author.strip()
        print('\n', author)

        feedback_content = await block.query_selector('div[class="_49x36f"]')
        feedback = await feedback_content.inner_text()
        print(feedback)

        url_answer = await compress_string(feedback)

        if url_answer in links:
            print('Такой комментарий уже есть в списке')
            continue

        author = f"{author}\n{url}"

        await generate_and_white(service=service,
                                 url_answer=url_answer,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)

    await browser.close()
    await playwright.stop()

async def main_2gis(url):
    service = await get_service()
    await check_2gis(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", 1)

if __name__ == '__main__':
    url = 'https://2gis.ru/tyumen/firm/70000001078903378/65.581594%2C57.166876/tab/reviews'
    asyncio.run(main_2gis(url))
