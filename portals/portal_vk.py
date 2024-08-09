import asyncio
import random
import time

import googleapiclient.errors
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

from selenium.webdriver.common.by import By

from utils.gs_editor import get_service, get_table_scope, pars_url
from utils.ai_module import generate_and_white
from utils.user_agent import get_soup, get_selenium
from utils.proxy_bridge import get_iplist
import os
from dotenv import load_dotenv

current_date = datetime.now()


dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

days_ago = int(os.environ.get("DAYS_AGO"))
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

async def check_vk(service, link, pattern, criteria, ss_id, project):
    print(link)
    ts = random.randint(5, 30)
    await asyncio.sleep(ts)

    links = await pars_url(service, ss_id, project)

    driver = await get_selenium(link)

    blocks = driver.find_elements(By.CSS_SELECTOR, 'div[id*="-"][class*="repl"][data-post-id*="-"]')
    len_b = len(blocks)
    print(len_b)

    if len_b == 0:
        blocks = driver.find_elements(By.CSS_SELECTOR, 'div[id*="post-"][class*="bp_post clear_fix "]')
        len_b = len(blocks)

    print(len_b)
    if len_b == 0:
        return

    for block in blocks:
        try:
            date = block.find_element(By.CSS_SELECTOR, 'span[class="rel_date"]').text.split(' ')
            print(date)

        except:
            continue

        day = int(date[0])
        month = await convert_date(date[1])
        year = int(date[2])

        target_date = datetime(year, month, day)
        formatted_date = target_date.strftime("%d.%m.%Y")
        print(formatted_date)

        if (current_date - target_date) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней = {date}.')
            continue

        url_answer = block.find_element(By.CSS_SELECTOR, 'a[class="wd_lnk"]').get_attribute('href')
        if url_answer in links:
            print('Такой комментарий уже есть в списке')
            continue

        author = block.find_element(By.CSS_SELECTOR, 'a[class="author author_highlighted"]').text
        print(author)
        print(url_answer)

        feedback = block.find_element(By.CSS_SELECTOR, 'div[class="wall_reply_text"]')
        print(feedback)

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
    url = 'https://vk.com/wall-11694885_373082?reply=373184'
    asyncio.run(check_vk(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", "Паритет"))