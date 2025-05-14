import os

import asyncio
from datetime import datetime, timedelta

import requests

from dotenv import load_dotenv

from selenium.webdriver.common.by import By

from utils.ai_module import generate_and_white
from utils.central_module import get_local_ip, get_hpo
from utils.gs_editor import pars_url, get_service
from utils.user_agent import get_soup, get_data_without_proxy, ua, get_selenium, get_selenium_proxy

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)
#
# current_date = datetime.now()
# record_date = current_date.strftime("%d.%m.%Y")
# now_month = current_date.month

days_ago = int(os.environ.get("DAYS_AGO"))

now_time = datetime.now()

# local_ip = asyncio.run(get_local_ip())
# if '176.124.192' in local_ip:
#     headless = True
#     proxy_on = True
#     only_text = False
#
# else:
#     print(f'local_ip Pikaby: {local_ip}')
#     headless = False
#     proxy_on = False
#     only_text = False

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
        "Referer": link,
        "DNT": "1",
        "Connection": "keep-alive"
    }

    payload = {
        "action": "get_comments_by_ids",
        "ids": 	"331307264,331352050,331347014,331206174,331388857,331203018,331213309,331204424,331204536,331204967,331214876,331197356,331202143,331196759,331222850,331200785,331195100,331204835,331221600,331203327,331210215,331197143,331227552,331198809,331206844,331195506,331228057,331232079,331239352,331278796,331201955,331203768,331214337,331232399,331202795,331249626,331256240,331287338,331298597,331306482"
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

async def blocks_pikabu(driver):
    try:
        more_comments = driver.find_element(By.CSS_SELECTOR, 'span.comments__more-count')
        more_comments.click()
    except:
        print('-- No more comments...')

    await asyncio.sleep(5)

    childrens = driver.find_elements(By.CSS_SELECTOR, 'div.comment-toggle-children__icon')
    print('-- Len childrens', len(childrens))

    # childrens = driver.find_elements(By.CSS_SELECTOR, 'div.comment-toggle-children comment-toggle-children_collapse')
    # print('-- Len childrens', len(childrens))
    #
    # input()

    for children in childrens:
        try:
            children.click()
            await asyncio.sleep(3)
            print('--- click...')

        except:
            continue

    blocks = driver.find_elements(By.CSS_SELECTOR, 'div[class="comment"]')
    return blocks

async def check_pikaby(service, url, pattern, criteria, ss_id, project, driver, links=False):
    if not links:
        links = await pars_url(service, ss_id, project)
    blocks = await blocks_pikabu(driver)

    print('Len', len(blocks))

    for block in blocks:
        date_content = block.find_element(By.CSS_SELECTOR, 'time[class="comment__datetime hint"]')
        date_full = date_content.get_attribute("datetime")
        if date_full in links:
            continue

        timestamp = datetime.strptime(date_full, '%Y-%m-%dT%H:%M:%S%z')
        date_ts = timestamp.timestamp()
        # Форматирование даты
        formatted_date = timestamp.strftime('%d.%m.%Y')

        parsed_datetime = timestamp.astimezone(None).replace(tzinfo=None)
        if (now_time - parsed_datetime) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней = {formatted_date}.')
            continue

        author = block.find_element(By.CSS_SELECTOR, 'span.user__nick').text
        try:
            feedback = block.find_element(By.CSS_SELECTOR, 'p.rv-comment').text
        except:
            continue

        await generate_and_white(service=service,
                                 url_answer=date_full,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)

    return driver


async def main_pikabu():
    headless, proxy_on, only_text = await get_hpo()

    url = 'https://pikabu.ru/story/spisok_sukhikh_kormov_iz_rf_dlya_koshek_i_sobak_9204451?cid=240886719'

    driver = await get_selenium_proxy(url=url, headless=headless, proxy=proxy_on)

    ss_id = '1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w'
    project = 'AlphaPet'
    service = await get_service()
    await check_pikaby(service, url, "pattern", "criteria", ss_id, project, driver)

    # # blocks = await blocks_pikabu_api(link)
    # #
    # # print(blocks)
    # #
    # # input()
    #
    #
    #
    # #link = 'https://pikabu.ru/story/otvet_na_post_kassir_pyaterochki_khotel_obmanut_pokupatelnitsu_12236720'
    # driver = await get_selenium_proxy(headless=headless, proxy=proxy_on)
    # driver.get(link)
    # await asyncio.sleep(2)
    #
    # blocks = await blocks_pikabu(driver)
    #
    # print('Len', len(blocks))
    #
    # for block in blocks:
    #     date_content = block.find_element(By.CSS_SELECTOR, 'time[class="comment__datetime hint"]')
    #     date_full = date_content.get_attribute("datetime")
    #     timestamp = datetime.strptime(date_full, '%Y-%m-%dT%H:%M:%S%z')
    #     date = timestamp.timestamp()
    #     # Форматирование даты
    #     formatted_date = timestamp.strftime('%d.%m.%Y')
    #
    #     if (time.time() - timestamp.timestamp()) <= 3 * 24 * 3600:
    #         print(f'--- Отзыв младше 3 дней = {formatted_date}.')
    #
    #     author = block.find_element(By.CSS_SELECTOR, 'span.user__nick').text
    #     try:
    #         feedback = block.find_element(By.CSS_SELECTOR, 'p.rv-comment').text
    #     except:
    #         continue
    #
    #     print(author, feedback)


if "__main__" in __name__:
    asyncio.run(main_pikabu())





