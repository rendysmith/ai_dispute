import asyncio
import json
import random
import os

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import zlib
import base64

from pprint import pprint

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils.gs_editor import get_service, get_table_scope, pars_url
from utils.ai_module import generate_and_white
from utils.user_agent import gen_ua, get_selenium, get_playwright, get_soup

from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

current_date = datetime.now()

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

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

async def check_ya_market(service, url, pattern, criteria, ss_id, project):
    print(f"New link = {url}")

    playwright, browser, page = await get_playwright(url)

    links = await pars_url(service, ss_id, project)
    ts = random.randint(5, max_sec)
    print(f'Wait {ts} sec...')
    await asyncio.sleep(ts)

    if not page:
        return 'Сайт не отдал данные.'

    await page.evaluate("document.body.style.zoom=0.5")

    blocks = await page.query_selector_all('div[class="eoZns"]')
    print(len(blocks))

    if not blocks:
        return "Страница не отдала данные"

    for block in blocks:
        date_content = await block.query_selector('span[class="ncho4"]')
        date = await date_content.inner_text()
        print("date", date)

        if not any(i in date for i in ['Неделю назад', 'дней назад', 'дня назад', 'вчера', 'день назад']):
            return

        link_content = await block.query_selector('div[data-apiary-widget-id]')
        url_answer = await link_content.get_attribute('data-apiary-widget-id')
        print("YAm url_answer", url_answer)

        if url_answer in links:
            continue

        author_content = await block.query_selector('span[class="_3WbcX"]')
        author = await author_content.inner_text()
        print(author)

        feedback_content = await block.query_selector('div[class="_1I3ni"]')
        feedback = await feedback_content.inner_text()
        print(feedback)

        if any(i in date for i in ['Неделю назад', 'дней назад', 'дня назад', 'вчера', 'день назад']):
            if '1' in date:
                day = current_date.day - 1

            elif '2' in date or 'Позавчера' in date:
                day = current_date.day - 2

            elif '3' in date:
                day = current_date.day - 3

            elif '4' in date:
                day = current_date.day - 4

            elif '5' in date:
                day = current_date.day - 5

            elif '6' in date:
                day = current_date.day - 6

            elif 'Неделю' in date:
                day = current_date.day - 7

            else:
                continue

            print(day)

            if day <= 0:
                day = 1

            month = current_date.month
            year = current_date.year
            print(year, month, day)

            target_date = datetime(year, month, day)
            formatted_date = target_date.strftime("%d.%m.%Y")
            print(formatted_date)

        else:
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


    await browser.close()
    await playwright.stop()









async def main():
    service = await get_service()


    url = 'https://market.yandex.ru/product--comfort-2/1913043741/reviews?sku=101282794585&uniqueId=1163401&do-waremd5=uhNIeXveQKQN_q2xrkkQIQ&grade_value=4&sort_by=date&sort_desc=1'

    url = 'https://market.yandex.ru/product/496791076/reviews'
    await check_ya_market(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", 1)

if __name__ == '__main__':
    asyncio.run(main())


