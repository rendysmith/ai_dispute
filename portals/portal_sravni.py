import asyncio
import base64
import os
import zlib
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

from utils.ai_module import generate_and_white
from utils.gs_editor import get_table_scope

current_date = datetime.now()

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)
days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

seven_days_ago = current_date - timedelta(days=days_ago)
formatted_7date = seven_days_ago.strftime('%Y-%m-%d')

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

async def pars_url(service, SS_ID, R_N):
    try:
        df = await get_table_scope(service, SS_ID, R_N)
        links = df['Link'].to_list()
    except:
        links = []
    return links


async def check_sravni(service, link, pattern, criteria, ss_id, project):
    links = await pars_url(service, ss_id, project)
    #       "https://www.sravni.ru/proxy-reviews/reviews/?filterBy=withRates&fingerPrint=2cf24b82de26a43cbc9961575a28d5ed&from=2024-05-04       &isClient=false&locationRoute=&newIds=true&orderBy=byPopularity&pageIndex=1&pageSize=10 &reviewObjectId=126810&reviewObjectType=insuranceCompany&specificProductId=&tag=&withVotes=true"
    url = f"https://www.sravni.ru/proxy-reviews/reviews/?filterBy=withRates&fingerPrint=2cf24b82de26a43cbc9961575a28d5ed&from={formatted_7date}&isClient=false&locationRoute=&newIds=true&orderBy=byPopularity&pageIndex=1&pageSize=100&reviewObjectId=147351&reviewObjectType=insuranceCompany&specificProductId=&tag=&withVotes=true"
    url = 'https://www.sravni.ru/proxy-reviews/reviews/?filterBy=withRates&fingerPrint=1a82bf4208be26b0cfc31659789b0174&isClient=false&locationRoute=&newIds=true&orderBy=byDate&pageIndex=0&pageSize=100&rated=any&reviewObjectId=147351&reviewObjectType=insuranceCompany&specificProductId=&tag=&withVotes=true'
    r = requests.get(url)
    if r.status_code == 200:
        r = r.json()

    else:
        return f'Сайт не отдал данные {r.status_code}'

    for i in r['items']:
        url_answer = f"{link}{i['id']}"
        if url_answer in links:
            continue

        if i['hasCompanyResponse'] == True:
            continue

        if i['commentsCount'] > 0:
            continue

        author = i['authorName']
        if i.get('authorLastName'):
            author = f"{author} {i['authorLastName']}"

        date_str = i['createdToMoscow']
        date_str_cleaned = date_str.split('.')[0] + '+00:00'
        dt = datetime.fromisoformat(date_str_cleaned)
        dt = dt.replace(tzinfo=None)

        if (current_date - dt) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней. = {dt}')
            return

        # Форматирование в нужный строковый формат
        formatted_date = dt.strftime('%d.%m.%Y')
        feedback = i['text']

        await generate_and_white(service=service,
                                 url_answer=url_answer,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)


async def main():
    from utils.gs_editor import get_service
    service = await get_service()
    url = 'https://www.sravni.ru/strakhovaja-kompanija/sberbank-strah/otzyvy/'
    await check_sravni(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", 1)

if __name__ == '__main__':
    asyncio.run(main())
