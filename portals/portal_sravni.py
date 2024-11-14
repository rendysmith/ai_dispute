import asyncio
import base64
import os
import zlib
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
from pandas import pivot
from pandas.io.stata import excessive_string_length_error

from utils.ai_module import generate_and_white
from utils.compressor import compress_string
from utils.converter import extract_company_name
from utils.gs_editor import get_table_scope, append_data_to_sheet_scope, pars_url
from utils.user_agent import get_data_with_proxy

current_date = datetime.now()

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)
days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

seven_days_ago = current_date - timedelta(days=days_ago)
formatted_7date = seven_days_ago.strftime('%Y-%m-%d')

companies = {'strakhovaja-kompanija/sberbank-strah': 147351}

async def get_top_url(link):
    pattern = r'https://www\.sravni\.ru/(.*?)/otzyvy/'
    link_company = await extract_company_name(pattern, link)

    if not link_company:
        return None, None

    return f"https://www.sravni.ru/{link_company}/otzyvy/", companies.get(link_company)

async def check_sravni(service, link, pattern, criteria, ss_id, project):
    top_url, reviewObjectId = await get_top_url(link)

    if top_url:
        datas = {'project': project,
                 'url': link,
                 'top_url': top_url}

        await append_data_to_sheet_scope(service, ss_id, 'unique_url', datas)

    else:
        return

    #https://www.sravni.ru/proxy-reviews/reviews/?filterBy=withRates&fingerPrint=-1&locationRoute=&newIds=true&orderBy=byDate&pageIndex=0&pageSize=10&rated=any&reviewObjectId=147351&reviewObjectType=insuranceCompany&specificProductId=&tag=&withVotes=true
    #https://www.sravni.ru/proxy-reviews/reviews/?filterBy=all&fingerPrint=90afd98450203b85cd796220e7680745&locationRoute=&newIds=true&orderBy=byDate&pageIndex=0&pageSize=10&rated=any&reviewObjectId=147351&reviewObjectType=insuranceCompany&specificProductId=&tag=&withVotes=true

    pageSize = "100"
    url = (f'https://www.sravni.ru/proxy-reviews/reviews/?filterBy=all&'
           f'fingerPrint=-1&'
           f'locationRoute=&'
           f'newIds=true&'
           f'orderBy=byDate&'
           f'pageIndex=0&'
           f'pageSize={pageSize}&'
           f'rated=any&reviewObjectId={reviewObjectId}&'
           f'reviewObjectType=insuranceCompany&specificProductId=&tag=&withVotes=true')

    print(url)
    #r = await get_data_with_proxy(url, text_format=False)
    #print(r)

    r = requests.get(url)

    if r.status_code == 200:
        r = r.json()
        print('-- Json OK!')

    else:
        #print(r.json())
        txt = f'-- Сайт не отдал данные {r.status_code}'
        print(txt)
        print(r.text)
        return txt

    links = await pars_url(service, ss_id, project)
    len_b = len(r['items'])
    print(len_b)

    for i in r['items']:
        url_answer = f"{link}{i['id']}"
        if url_answer in links:
            continue

        if i['hasCompanyResponse'] == True: #есть ответ компании
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
            continue

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
    url = 'https://www.sravni.ru/strakhovaja-kompanija/sberbank-strah/otzyvy/575086/'
    await check_sravni(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", 'СберСтрахование_3')

if __name__ == '__main__':
    asyncio.run(main())
