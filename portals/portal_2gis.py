import json
from pprint import pprint

import asyncio
import random

from selenium.webdriver.common.by import By

from datetime import datetime, timedelta, timezone

from utils.central_module import get_local_ip, wait_for_portal, get_hpo
from utils.compressor import compress_string
from utils.gs_editor import pars_url, get_service, append_data_to_sheet_scope
from utils.ai_module import generate_and_white
from utils.user_agent import get_soup, get_selenium_proxy

from utils.constants import months

import os
from dotenv import load_dotenv

current_date = datetime.now(timezone.utc)

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

# local_ip = asyncio.run(get_local_ip())
# if '176.124.192' in local_ip:
#     headless = True
#     proxy_on = True
#     only_text = False
#
# else:
#     print(f'local_ip 2Gis: {local_ip}')
#     headless = True
#     proxy_on = False
#     only_text = False

async def get_id_obj(url):
    url_split = url.split('/')
    print("url_split", url_split)
    #city_company = url_split[3]

    for idx, v in enumerate(url_split):
        if v == 'firm':
            id_obj = url_split[idx+1]
            break

        elif v == 'orgs':
            id_obj = url_split[idx + 1]
            break

        elif v == 'geo':
            id_obj = url_split[idx + 1]
            break

    return id_obj

async def send_top_url(service, ss_id, project, url):
    id_obj = await get_id_obj(url)
    top_url = f'https://2gis.ru/firm/{id_obj}'
    print(top_url)

    datas = {'project': project,
             'url': url,
             'top_url': top_url}

    await append_data_to_sheet_scope(service, ss_id, 'unique_url', datas)
    return id_obj, top_url

async def soup_pars(service, links, id_org, pattern, criteria, ss_id, project):
    url = f'https://public-api.reviews.2gis.com/2.0/branches/{id_org}/reviews?limit=50&is_advertiser=true&fields=meta.providers,meta.branch_rating,meta.branch_reviews_count,meta.total_count,reviews.hiding_reason,reviews.is_verified&without_my_first_review=false&rated=true&sort_by=date_created&key=b0209295-ae15-48b2-acb2-58309b333c37&locale=ru_RU'
    print(url)

    headless, proxy_on, only_text = await get_hpo()
    r_json = await get_soup(url, only_text=False, proxy=proxy_on)

    blocks = r_json['reviews']
    print(f'Len_B = {len(blocks)}')

    for block in blocks:
        date_content = block['date_created']
        date = datetime.strptime(date_content, "%Y-%m-%dT%H:%M:%S.%f%z")

        if (current_date - date) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней. = {date}')
            return

        url_answer = block['id']
        if url_answer in links:
            print('Такой комментарий уже есть в списке')
            continue

        official_answer = block['official_answer']
        if not official_answer:
            print("Уже есть ответ компании.")
            continue

        formatted_date = date.strftime("%d.%m.%Y")
        print(formatted_date)

        feedback = block['text']

        author = block['user']['name']
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

async def pars_json_data(script_text):
    script_text = script_text.replace('\\"', '')
    script_text = script_text.replace('\\', '')
    # Найти начало JSON
    json_start = script_text.find('"review":')
    #print(json_start)
    if json_start == -1:
        raise ValueError("Начало JSON не найдено")

    # Баланс скобок
    balance = 0
    json_end = None
    turn_off = False

    # Ищем конец JSON-объекта
    len_s = len(script_text)

    for i in range(json_start, len_s - json_start):

        char = script_text[i]
        if char == '{':
            balance += 1
            turn_off = True

        elif char == '}':
            balance -= 1

        # Если баланс = 0, это конец JSON
        if balance == 0 and turn_off:
            json_end = i
            print(f'Break {i}')
            break

    #print(json_end)
    if json_end is None:
        raise ValueError("Конец JSON не найден")

    # Извлекаем JSON-строку
    json_str = script_text[json_start:json_end + 1]


    #print("Извлечённый JSON:", json_str)
    json_str = "{" + json_str + "}"  # Предварительный JSON словарь
    #print(json_str)

    data_dict = json.loads(json_str)
    #pprint(data_dict)

    return data_dict

async def selen_pars(service, links, top_url, pattern, criteria, ss_id, project):
    top_url = top_url + '/tab/reviews'

    headless, proxy_on, only_text = await get_hpo()
    driver = await get_selenium_proxy(top_url, headless=headless, proxy=proxy_on)
    await wait_for_portal() #Время ожидания
    json_data_content = driver.find_elements(By.CSS_SELECTOR, 'script')

    data_dict = None
    for script in json_data_content:
        script_text = script.get_attribute('innerHTML')
        if 'initialState =' in script_text:
            data_dict = await pars_json_data(script_text)
            pprint(data_dict)
            break

    if not data_dict:
        return

    if not isinstance(data_dict, dict):
        return

    blocks = data_dict['review']

    for k, block in blocks.items():
        date_content = block['data']['date_created']
        date = datetime.strptime(date_content, "%Y-%m-%dT%H:%M:%S.%f%z")

        if (current_date - date) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней. = {date}')
            continue

        url_answer = block['data']['id']
        if url_answer in links:
            print('Такой комментарий уже есть в списке')
            continue

        official_answer = block['data']['official_answer']
        if not official_answer:
            print("Уже есть ответ компании.")
            continue

        formatted_date = date.strftime("%d.%m.%Y")
        print(formatted_date)

        feedback = block['data']['text']

        author = block['data']['user']['name']
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

    try:
        driver.quit()
    except:
        pass

async def check_2gis(service, url, pattern, criteria, ss_id, project, links=False):
    if not links:
        links = await pars_url(service, ss_id, project)

    id_org, top_url = await send_top_url(service, ss_id, project, url)

    if any(fo in url for fo in ['firm', 'orgs']):
        await soup_pars(service, links, id_org, pattern, criteria, ss_id, project)

    elif 'geo' in url:
        await selen_pars(service, links, top_url, pattern, criteria, ss_id, project)

async def main_2gis(url):
    service = await get_service()
    #playwright, browser, page = await get_playwright(url)
    await check_2gis(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", "НовикомБанк")

if __name__ == '__main__':

    url = 'https://2gis.ru/irkutsk/geo/1548773796872222/104.211407%2C52.355866?m=104.209969%2C52.352144%2F16'
    url = 'https://2gis.ru/firm/70000001006477930'

    asyncio.run(main_2gis(url))
    print('OK!')

