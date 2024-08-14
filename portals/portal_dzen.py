import asyncio
import random

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import zlib
import base64

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils.gs_editor import get_service, get_table_scope, pars_url
from utils.ai_module import generate_and_white
from utils.user_agent import gen_ua, get_selenium

# Настройка опций Chrome для работы в headless-режиме
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# Инициализация драйвера
driver = webdriver.Chrome(options=chrome_options)

current_date = datetime.now()

async def check_dzen(service, url, pattern, criteria, ss_id, project):
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


if __name__ == '__main__':
    service = asyncio.run(get_service())
    url = 'https://dzen.ru/a/ZpTppvyvWw9ewvtn'
    url = 'https://dzen.ru/b/Y0FV3tbF3mAKE8E8#comment_1348850413'
    url = 'https://dzen.ru/a/ZpTppvyvWw9ewvtn'
    asyncio.run(check_dzen(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", "Паритет"))
