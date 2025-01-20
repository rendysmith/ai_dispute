import asyncio
import time
from datetime import datetime
from pprint import pprint

import requests

from selenium.webdriver.common.by import By

from utils.central_module import get_local_ip
from utils.user_agent import get_soup, get_data_without_proxy, ua, get_selenium, get_selenium_proxy

local_ip = asyncio.run(get_local_ip())
if '176.124.192' in local_ip:
    headless = True
    proxy_on = True
    only_text = False

else:
    print(f'local_ip: {local_ip}')
    headless = False
    proxy_on = False
    only_text = False

async def blocks_pikabu_api(link):
    """Не могу найти данные для запроса а именно ids"""


    url = 'https://pikabu.ru/ajax/comments_actions.php'

    headers = {
        "User-Agent": ua.random,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Csrf-Token": "709dc6558eeb462b193fa28d868ef2ad",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://pikabu.ru",
        "Referer": "https://pikabu.ru/story/korporativnyiy_chellendzh_dobra_12082740",
        "DNT": "1",
        "Connection": "keep-alive"
    }

    payload = {
        "action": "get_comments_by_ids",
        "ids": "191517555,191517881,191517647,249343914,211591942,209137588,191517551,191517411,191517597"
    }

    # Выполняем POST-запрос
    response = requests.post(url, headers=headers, data=payload)
    print(response)

    # Проверяем статус и выводим результат
    if response.status_code == 200:
        blocks = response.json()['data']
        print(len(blocks))
        return blocks

    else:
        print(f"Ошибка: {response.status_code}")
        return


async def blocks_pikabu(driver, link):
    try:
        more_comments = driver.find_element(By.CSS_SELECTOR, 'span.comments__more-count')
        more_comments.click()
    except:
        print('-- No more comments...')

    await asyncio.sleep(5)

    blocks = driver.find_elements(By.CSS_SELECTOR, 'div[class="comment"]')

    return blocks



async def main_pikabu():
    link = 'https://pikabu.ru/story/10_luchshikh_torrentobmennikov_v_rossii_aktivnyikh_v_2021_7995137#comments'
    #link = 'https://pikabu.ru/story/otvet_na_post_kassir_pyaterochki_khotel_obmanut_pokupatelnitsu_12236720'
    driver = await get_selenium_proxy(headless=headless, proxy=proxy_on)
    blocks = await blocks_pikabu(driver, link)

    for block in blocks:
        date_content = block.find_element(By.CSS_SELECTOR, 'time[class="comment__datetime hint"]')
        date_full = date_content.get_attribute("datetime")
        timestamp = datetime.strptime(date_full, '%Y-%m-%dT%H:%M:%S%z')

        # Форматирование даты
        formatted_date = timestamp.strftime('%d.%m.%Y')
        print(time.time(), timestamp.timestamp())
        print(time.time() - timestamp.timestamp())

        if (time.time() - timestamp.timestamp()) <= 3 * 24 * 3600:
            print(f'--- Отзыв младше 3 дней = {formatted_date}.')


if "__main__" in __name__:
     asyncio.run(main_pikabu())




