import asyncio
import os
import random

import requests

from datetime import datetime, timedelta
import time

from dotenv import load_dotenv

from selenium.webdriver.common.by import By

from utils.gs_editor import get_service, get_table_scope, pars_url
from utils.ai_module import generate_and_white
from utils.user_agent import get_playwright

current_date = datetime.now()

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

async def check_dzen_sel(service, url, pattern, criteria, ss_id, project):
    links = await pars_url(service, ss_id, project)
    ts = random.randint(5, 6)
    print(f'Wait {ts} sec...')
    await asyncio.sleep(ts)

    driver = await get_selenium(url)

    zen_object_id = driver.find_element(By.CSS_SELECTOR, 'meta[property="zen_object_id"]').get_attribute('content').split(':')
    print(zen_object_id)
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
        return

    UsersByID = {v['uidSafe']: v['displayName'] for k, v in r['usersById'].items()}
    print(UsersByID)

    for block in r['items']:
        print(block)
        url_answer = block['entityData']['id']
        print(url_answer)

        if url_answer in links:
            print('Такой комментарий уже есть в списке')
            continue

        date = block['entityData']['createdTs']/1000

        if (time.time() - date) > 7 * 24 * 3600:
            print(f'--- Отзыв старше 30 дней = {date}.')
            continue

        date = datetime.fromtimestamp(timestamp_sec)
        # Форматирование даты
        formatted_date = date.strftime('%d.%m.%Y')
        print(formatted_date)

        #authorSafeUid = block['authorSafeUid']
        author = UsersByID[block['entityData']['authorSafeUid']]
        print(author)

        await generate_and_white(service=service,
                                 url_answer=url_answer,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)


async def check_dzen(service, url, pattern, criteria, ss_id, project):
    playwright, browser, page = await get_playwright(url)

    links = await pars_url(service, ss_id, project)
    ts = random.randint(5, max_sec)
    print(f'Wait {ts} sec...')
    await asyncio.sleep(ts)

    if not page:
        return 'Сайт не отдал данные.'

    try:
        zen_object_id_content = await page.query_selector('meta[property="zen_object_id"]')
        zen_object_id = await zen_object_id_content.get_attribute('content')
        zen_object_id = zen_object_id.split(':')

    except:
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

    if len_r == 0:
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

        if (time.time() - date) > 7 * 24 * 3600:
            print(f'--- Отзыв старше 30 дней = {date}.')
            continue

        date = datetime.fromtimestamp(timestamp_sec)
        # Форматирование даты
        formatted_date = date.strftime('%d.%m.%Y')
        #print(formatted_date)

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


if __name__ == '__main__':
    service = asyncio.run(get_service())

    url = 'https://dzen.ru/a/ZF3kG27fcA39RZbS#comment_1650504031'
    asyncio.run(check_dzen(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", "Паритет"))
