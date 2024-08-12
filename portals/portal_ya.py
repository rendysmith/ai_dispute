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


async def check_ya(service, url, pattern, criteria, ss_id, project):
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
        input()

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
    service = await get_service()
    url = 'https://market.yandex.ru/product--cordiant-snow-cross-2-zimniaia-shipovannaia/177735076/reviews?_redirectCount=1'

    url = 'https://dzen.ru/a/ZpTppvyvWw9ewvtn'
    #
    # headers = await gen_ua('https://dzen.ru')
    #
    # response = requests.get(url, headers=headers)
    # html_content = response.text
    #
    # # Анализ HTML с помощью BeautifulSoup
    # soup = BeautifulSoup(html_content, 'html.parser')
    # for script in soup.find_all('script'):
    #     if 'api/comments/v2/root-comments' in script.text:
    #         json_url = script.text.split('"')[1]  # Получаем URL
    #         break
    #
    # print(json_url)

    #input(soup)


    #url = 'https://dzen.ru/api/comments/v2/root-comments?documentId=native%3A6694e9a6fcaf5b0f5ec2fb67&publicationPublisherId=5930fb857ddde84c29e24b43&batchSize=3&withConfig=true&sessionTs=1723453482421&clientTs=1723453482422&subscriptionStateFor=currentUser&updateDefaultSorting=false&withCurrentUser=true&rid=1258414138.2801038807.2695878971389038.401557352&rnd=1723453482422'
    #url = 'https://dzen.ru/api/comments/v2/root-comments?documentId=native%3A6694e9a6fcaf5b0f5ec2fb67&publicationPublisherId=5930fb857ddde84c29e24b43'

    await check_ya(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", "Паритет")

if __name__ == '__main__':
    asyncio.run(main())

