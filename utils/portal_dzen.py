import asyncio
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

from utils.gs_editor import get_service, get_table_scope
from utils.ai_module import generate_and_white

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

async def pars_url(service, SS_ID, R_N):
    try:
        df = await get_table_scope(service, SS_ID, R_N)
        links = df['Link'].to_list()
    except:
        links = []
    return links

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


async def check_dzen(service, url, pattern, criteria, ss_id, project):
    links = await pars_url(service, ss_id, project)

    print(url)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows; Windows NT 10.0; Win64; x64; en-US) Gecko/20130401 Firefox/60.6'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    print(soup)

    blocks = soup.find_all('div', {'class': 'comment__block-34 comment__root-wu'})
    print(len(blocks))

    driver.get(url)
    print(driver.page_source)
    # Ожидание загрузки определенного элемента (например, заголовка)
    wait = WebDriverWait(driver, 10)
    blocks = driver.find_elements(By.CSS_SELECTOR, 'div[class="comment__block-34 comment__root-wu"]')
    print(len(blocks))

    input()





























    for block in blocks:
        date = block.find_element(By.CSS_SELECTOR, 'div[class="_4mwq3d"]').text.split(', ')[0].split(' ')
        print(date)

        year = int(date[2])
        month = await convert_date(date[1])
        day = int(date[0])

        target_date = datetime(year, month, day)
        formatted_date = target_date.strftime("%d.%m.%Y")
        print(formatted_date)

        if (current_date - target_date) > timedelta(days=30):
            print(f'--- Отзыв старше 30 дней = {date}.')
            continue

        try:
            answer = block.find_element(By.CSS_SELECTOR, 'div[class="_sgs1pz"]')
            print('Уже есть ответ на комментарий')
            continue

        except:
            pass

        author = block.find_element(By.CSS_SELECTOR, 'span[class="_16s5yj36"]').text.strip()
        print('\n', author)

        feedback = block.find_element(By.CSS_SELECTOR, 'div[class="_49x36f"]').text
        print(feedback)

        url_answer = await compress_string(feedback)

        if url_answer in links:
            print('Такой комментарий уже есть в списке')
            continue

        author = f"{author}\n{url}"

        await generate_and_white(service=service,
                                 url_answer=url_answer,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)

        time.sleep(7)


# if __name__ == '__main__':
#     service = asyncio.run(get_service())
#     url = 'https://2gis.ru/tyumen/firm/70000001078903378/tab/reviews'
#     asyncio.run(check_2gis(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", "Паритет"))
#
#     print('Отметка о выполнении')
#     data = {'service_name': 'PRAVDA', 'date': time.ctime()}
#     asyncio.run(skillbox_sheet(service, '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8', 'logs', data))