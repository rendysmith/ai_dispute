import asyncio
import random
import time

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

from utils.gs_editor import get_service, get_table_scope, pars_url
from utils.ai_module import generate_and_white
from utils.user_agent import gen_ua, get_soup
from utils.proxy_bridge import get_iplist

current_date = datetime.now()

import os
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

login_proxy = os.environ.get("LOGIN_PROXY")
pass_proxy = os.environ.get("PASS_PROXY")

async def convert_date(month):
    months = {
        'янв': 1,
        'фев': 2,
        "мар": 3,
        "апр": 4,
        "мая": 5,
        "июн": 6,
        "июл": 7,
        "авг": 8,
        "сен": 9,
        "окт": 10,
        "ноя": 11,
        "дек": 12
    }
    return months[month]

async def check_otzovik(service, link, pattern, criteria, ss_id, project):
    ts = random.randint(5, max_sec)
    print(f'Wait {ts} sec...')
    await asyncio.sleep(ts)

    links = await pars_url(service, ss_id, project)

    # print(link)
    # soup = await get_soup(link)
    # top_link = soup.find('h1', {"class": "product-name"})
    # top_url = "https://otzovik.com" + top_link.find('a')['href'] + '?order=date_desc'
    # print(top_link)

    soup = await get_soup(link)
    if not soup:
        return 'Сайт не отдал данные!'

    blocks = soup.find_all("div", {"class": "comment"})
    print(len(blocks))

    if len(blocks) == 0:
        return

    for block in blocks:
        url_answer = block['id']
        if url_answer in links:
            print("Такой комментарий уже отмечен")
            continue

        date_content = block.find("div", {"class": "comment-postdate ts"}).text.strip().split(' ')
        #print(type(date_content))
        #print(date_content)
        try:
            year = int(date_content[2])
        except:
            year = int(datetime.now().year)

        month = await convert_date(date_content[1])
        day = int(date_content[0])
        #hour = int(date_content[-1][0:2])

        target_date = datetime(year, month, day)

        if (current_date - target_date) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней. = {target_date}')
            return

        author = block.find("a", {"class": "user-login"}).text

        formatted_date = date.strftime("%d.%m.%Y")
        #print(formatted_date)

        feedback = block.find("div", {"class": "comment-body"}).text

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
    # host_port = asyncio.run(get_iplist())
    #
    # proxies = {
    #     'http': f'http://{login_proxy}:{pass_proxy}@{host_port}',
    #     'https': f'https://{login_proxy}:{pass_proxy}@{host_port}'
    # }
    #
    # print(proxies)
    # response = requests.get("http://api.ipify.org/", proxies=proxies)
    # print(response.text)
    #
    #
    # response = requests.get("http://ipwho.is/", proxies=proxies)
    # print(response.json()['continent'])
    # print(response.json()['country'])


    service = asyncio.run(get_service())
    url = 'https://otzovik.com/review_15319091.html'
    asyncio.run(check_otzovik(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", "Паритет"))