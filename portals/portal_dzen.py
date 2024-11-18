import asyncio
import os
import random

import requests

from datetime import datetime, timedelta
import time

from dotenv import load_dotenv

from selenium.webdriver.common.by import By

from portals.portal_otzovik import headless, proxy_on
from utils.gs_editor import get_service, get_table_scope, pars_url
from utils.ai_module import generate_and_white
from utils.user_agent import get_selenium_proxy

current_date = datetime.now()

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

headless = True
proxy_on = True

async def check_dzen(service, url, pattern, criteria, ss_id, project, driver):

    # driver = await get_selenium_proxy(url, headless=headless, proxy=proxy_on)
    # driver.get(url)

    zen_object_id = driver.find_element(By.CSS_SELECTOR, 'meta[property="zen_object_id"]').get_attribute('content').split(':')
    #print(zen_object_id)
    documentId = zen_object_id[1]
    publicationPublisherId = zen_object_id[0]

    url_json = f'https://dzen.ru/api/comments/v2/root-comments?documentId=native%3A{documentId}&publicationPublisherId={publicationPublisherId}'
    r = requests.get(url_json).json()
    len_r = len(r['items'])

    if len_r == 0:
        url_json = f'https://dzen.ru/api/comments/v2/root-comments?documentId=brief%3A{documentId}&publicationPublisherId={publicationPublisherId}'
        r = requests.get(url_json).json()
        len_r = len(r['items'])

    if len_r == 0:
        driver.quit()
        return

    UsersByID = {v['uidSafe']: v['displayName'] for k, v in r['usersById'].items()}
    #print(UsersByID)
    links = await pars_url(service, ss_id, project)

    for block in r['items']:
        #print(block)
        url_answer = block['entityData']['id']
        #print(url_answer)

        if url_answer in links:
            print('Такой комментарий уже есть в списке')
            continue

        date = block['entityData']['createdTs']/1000
        #print(date)

        # Форматирование даты
        date_content = datetime.fromtimestamp(date)
        formatted_date = date_content.strftime('%d.%m.%Y')

        if (time.time() - date) > 7 * 24 * 3600:
            print(f'--- Отзыв старше 30 дней = {formatted_date}.')
            continue

        #date = datetime.fromtimestamp(timestamp_sec)

        #print(formatted_date)

        #authorSafeUid = block['authorSafeUid']
        author = UsersByID[block['entityData']['authorSafeUid']]
        #print(author)

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

async def check_dzen_old(service, url, pattern, criteria, ss_id, project, playwright, browser, page):
    #playwright, browser, page = await get_playwright(url)

    links = await pars_url(service, ss_id, project)

    if not page:
        # await browser.close()
        # await playwright.stop()
        return 'Сайт не отдал данные.'

    try:
        zen_object_id_content = await page.query_selector('meta[property="zen_object_id"]')
        zen_object_id = await zen_object_id_content.get_attribute('content')
        zen_object_id = zen_object_id.split(':')

    except:
        await browser.close()
        await playwright.stop()
        return 'Сайт не отдал данные.'

    #print(zen_object_id)
    documentId = zen_object_id[1]
    publicationPublisherId = zen_object_id[0]

    url_json = f'https://dzen.ru/api/comments/v2/root-comments?documentId=native%3A{documentId}&publicationPublisherId={publicationPublisherId}'
    r = requests.get(url_json).json()
    len_r = len(r['items'])

    if len_r == 0:
        url_json = f'https://dzen.ru/api/comments/v2/root-comments?documentId=brief%3A{documentId}&publicationPublisherId={publicationPublisherId}'
        r = requests.get(url_json).json()
        len_r = len(r['items'])

    print(len_r)
    if len_r == 0:
        await browser.close()
        await playwright.stop()
        return

    UsersByID = {v['uidSafe']: v['displayName'] for k, v in r['usersById'].items()}
    #print(UsersByID)

    for block in r['items']:
        #print(block)
        url_answer = block['entityData']['id']
        #print(url_answer)

        if url_answer in links:
            print('Такой комментарий уже есть в списке')
            continue

        date = block['entityData']['createdTs']/1000
        print(date)

        if (time.time() - date) > 7 * 24 * 3600:
            print(f'--- Отзыв старше 30 дней = {date}.')
            continue

        # Форматирование даты
        #formatted_date = date.strftime('%d.%m.%Y')
        formatted_date = datetime.fromtimestamp(date).strftime('%d.%m.%Y')

        #authorSafeUid = block['authorSafeUid']
        author = UsersByID[block['entityData']['authorSafeUid']]
        #print(author)

        feedback = block['entityData']['text']
        #input(feedback)

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

async def main_dzen():
    service = await get_service()

    url = 'https://dzen.ru/a/Y1o2zJjP7VPVFVdJ'
    await check_dzen(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", "Паритет")

if __name__ == '__main__':
    asyncio.run(main_dzen())
