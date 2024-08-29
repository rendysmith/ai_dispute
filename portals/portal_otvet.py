import asyncio
import json
import random

from datetime import datetime, timedelta, timezone

from selenium.webdriver.common.by import By
from pprint import pprint

from utils.gs_editor import get_service, get_table_scope, pars_url
from utils.ai_module import generate_and_white
from utils.user_agent import get_soup, get_selenium, get_playwright

import os
from dotenv import load_dotenv

now = datetime.now(timezone.utc)
current_date = now

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

login_proxy = os.environ.get("LOGIN_PROXY")
pass_proxy = os.environ.get("PASS_PROXY")

async def compress_string(input_string):
    # Сжимаем строку с помощью zlib
    compressed_data = zlib.compress(input_string.encode('utf-8'))
    # Кодируем сжатые данные в Base64 для удобства хранения и передачи
    compressed_base64 = base64.b64encode(compressed_data)
    return compressed_base64.decode('utf-8')

async def convert_date(month):
    months = {
        'янв': 1,
        'Jan': 1,
        'фев': 2,
        'Feb': 2,
        "мар": 3,
        'Mar': 3,
        "апр": 4,
        'Apr': 4,
        "мая": 5,
        'May': 5,
        "июн": 6,
        'Jun': 6,
        "июл": 7,
        'Jul': 7,
        "авг": 8,
        'Aug': 8,
        "сен": 9,
        'Sep': 9,
        "окт": 10,
        'Oct': 10,
        "ноя": 11,
        'Nov': 11,
        "дек": 12,
        'Dec': 12,
    }
    return months[month]


async def check_otvet(service, link, pattern, criteria, ss_id, project):
    print(link)

    ts = random.randint(5, max_sec)
    print(f'Wait {ts} sec...')
    await asyncio.sleep(ts)

    soup = await get_soup(link)
    if not soup:
        return 'Сайт не отдал данные!'
    #print(soup)
    print('========================================================')
    script_tag = soup.find_all('script')
    #print(len(script_tag))
    for i in script_tag:
        if 'Скорее всего из-за' in str(i):
            #print(f"*****************************************************\n{i}\n{type(i.text)}\n{i.text}\n---------------------------------------")
            try:
                text = i.text.replace('var QST_JSON = ', '').replace(';', '')
                #print(text)
                datas = json.loads(text)
                #print('+++++++++++++++++++++++++++++++++++++++')
                #print(type(datas))
                #input(datas)
            except:
                #input('Next...')
                return 'Данные не получены'
    #
    # pprint(datas)
    # input()

    if datas.get('@graph'):
        blocks = datas['@graph']
        print('--- Новые данные!!!')

    elif datas.get('result'):
        blocks = datas['result']['answers']

        for block in blocks:
            date_content = block['created_at']
            date = datetime.strptime(date_content, "%Y-%m-%dT%H:%M:%S%z")
            formatted_date = date.strftime("%d.%m.%Y")
            print(date)
            if (current_date - date) > timedelta(days=days_ago):
                print(f'--- Отзыв старше {days_ago} дней = {formatted_date}.')
                continue

            feedback = block['data']['content'][0]['text']
            print(feedback)

            author = block['author']['data']['nick']
            print(author)

            url_answer = await compress_string(feedback)

            if url_answer in links:
                print('Такой комментарий уже есть в списке')
                continue

            await generate_and_white(service=service,
                                     url_answer=url_answer,
                                     author=author,
                                     formatted_date=formatted_date,
                                     ss_id=ss_id,
                                     project=project,
                                     feedback=feedback,
                                     pattern=pattern,
                                     criteria=criteria)


if __name__ == '__main__':

    service = asyncio.run(get_service())
    url = 'https://vk.com/wall-11694885_373082?reply=373184'
    url = 'https://otvet.mail.ru/question/233383266'
    asyncio.run(check_otvet(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", "AlphaPet"))