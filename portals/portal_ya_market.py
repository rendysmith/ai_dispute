import asyncio
import json
import random
import os

import requests
import selenium.common.exceptions
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
from utils.user_agent import gen_ua, get_selenium, get_soup, get_selenium_proxy
from utils.constants import months

from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

current_date = datetime.now()

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

async def check_ya_market_new(driver):
    json_data = driver.find_element(By.CSS_SELECTOR, 'noframes[data-apiary="patch"]').text
    print(json_data)
    print('----------------------')

    blocks = driver.find_elements(By.CSS_SELECTOR, 'div[data-apiary-widget-name="@card/ReviewItem"]')
    print(len(blocks))

async def check_ya_market(service, url, pattern, criteria, ss_id, project, driver, links=False):
    print(f"New link = {url}")

    await asyncio.sleep(10)

    try:
        click_checkbox = driver.find_element(By.CSS_SELECTOR, 'input[class="CheckboxCaptcha-Button"]')
        click_checkbox.click()

    # except Exception as Ex:
    #     i_am_robot = driver.find_element(By.CSS_SELECTOR, 'span[id="checkbox-label"]')
    #     print(i_am_robot==True)
    #     return "Antibot"

    except selenium.common.exceptions.NoSuchElementException as NSEE:

        print('- No CheckBox and antibot')

    if not links:
        links = await pars_url(service, ss_id, project)

    if not driver:
        driver.quit()
        # await playwright.stop()
        return 'Сайт не отдал данные.'

    #await page.evaluate("document.body.style.zoom=0.5")
    driver.execute_script("document.body.style.zoom='0.5'")

    # page = driver.page_source
    # if 'в этом ценовом диапазоне выбор' in str(page):
    #     input('Есть заметка')

    await asyncio.sleep(5)

    #blocks = await page.query_selector_all('div[class="eoZns"]')
    blocks = driver.find_elements(By.CSS_SELECTOR, 'div[class="eoZns"]')
    print(len(blocks))

    if not blocks:
        blocks = driver.find_elements(By.CSS_SELECTOR, 'div[data-apiary-widget-name="@card/ReviewItem"]')
        print(len(blocks))
        if not blocks:
            #driver.quit()
            return "Страница не отдала данные"

    for block in blocks:
        try:
            link_content = block.find_element(By.CSS_SELECTOR, 'div[data-apiary-widget-id]')
            url_answer = link_content.get_attribute("data-apiary-widget-id")
        except:
            #print(block.get_attribute('outerHTML'))
            url_answer = block.get_attribute('id')

        print("YAm url_answer:", url_answer)

        if url_answer in links:
            continue

        try:
            try:
                date = block.find_element(By.CSS_SELECTOR, 'span[class="ncho4"]').text
            except:
                date = block.find_element(By.CSS_SELECTOR, 'div[data-auto="created-date"]').text

            print(date)

            if not any(i in date.lower() for i in ['неделю назад', 'дней назад', 'дня назад', 'вчера', 'день назад']):
                print('NO DATE')
                return

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

            author_text = block.find_element(By.CSS_SELECTOR, 'span[class="_3WbcX"]').text
            author = f"{author_text}, {url}"
            print(author)

            feedback = block.find_element(By.CSS_SELECTOR, 'div[class="_1I3ni"]').text
            print(feedback)
            print('------TRY--------')

        except:
            date_content = block.find_element(By.CSS_SELECTOR, 'div[class="ds-textLine ds-textLine_gap_2"][data-auto="created-date"]').text
            date_split = date_content.split(' ')
            if len(date_split) == 2:
                data_int = int(date_split[0])
                month = months[date_split[1]]
                year = current_date.year

            else:
                return

            target_date = datetime(year, month, data_int)
            formatted_date = target_date.strftime("%d.%m.%Y")
            print(formatted_date)

            author = block.find_element(By.CSS_SELECTOR, 'span[itemprop="name"][data-auto="nickname"]').text
            print(author)

            feedback = block.find_element(By.CSS_SELECTOR, 'div[class="_2lqnk"]').text
            print(feedback)
            print('------EXCTRA--------')

        await generate_and_white(service=service,
                                 url_answer=url_answer,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)


    driver.quit()









async def main():
    service = await get_service()

    url = 'https://market.yandex.ru/product--cordiant-snow-cross-2-zimniaia-shipovannaia/177735076/reviews?no-pda-redir=1&sort_by=date&page=5'
    url = 'https://market.yandex.ru/product--sport-3/10682420/reviews?sku=101282723653&uniqueId=10698030&do-waremd5=Zw1mXQ0cMnQecAKjfF4EbQ&grade_value=1&sort_by=date&sort_desc=1'

    driver = await get_selenium_proxy(url, False, False)

    await asyncio.sleep(5)
    await check_ya_market(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", "Кордиант", driver)

    #await check_ya_market_new(driver)

if __name__ == '__main__':
    asyncio.run(main())


