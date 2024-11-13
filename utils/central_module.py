import os
import random
import re
import time

import asyncio
import traceback

import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from utils.constants import TABLES_LIST
from utils.gs_editor import append_data_to_sheet_scope
from utils.user_agent import get_playwright, get_selenium_proxy

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

token_proxy = os.environ.get("TOKEN_PROXY")
id_proxy = os.environ.get("ID_PROXY")

max_sec = int(os.environ.get("MAX_SEC"))
ss_id = TABLES_LIST['zoom']

async def get_api_service():
    url = f'https://api.proxy5.net/api/service/{id_proxy}'
    headers = {
        'Authorization': f'Basic {token_proxy}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    response = requests.get(url, headers=headers)
    print(response)
    r_json = response.json()
    print(r_json)
    print(f'Binded IP: {r_json.get("bindedip")}')
    return r_json

async def proxy_status():
    proxy_action = await get_api_service()
    return proxy_action['status']

async def wait_for_portal():
    ts = random.randint(5, max_sec)
    print(f'Wait {ts} sec...')
    await asyncio.sleep(ts)

async def get_set():
    url = 'http://147.45.164.92/json/parsing.php'
    r = requests.get(url)
    status_code = r.status_code
    if status_code == 200:
        r_json = r.json()
        timetable = [k for k, v in r_json['Timetable'].items() if v == 'True']
        projects = [k for k, v in r_json['projects'].items() if v == 'True']
        portal = [k for k, v in r_json['portal'].items() if v == 'True']
        return timetable, projects, portal

    else:
        return [], [], []

async def get_local_ip():
    url = 'https://api.myip.com/'
    r = requests.get(url)
    if r.status_code == 200:
        if r.json().get('ip'):
            return r.json()['ip']

    url = 'https://api.ipify.org?format=json'
    r = requests.get(url)
    if r.status_code == 200:
        if r.json().get('ip'):
            return r.json()['ip']

    url = 'https://ifconfig.me/all.json'
    r = requests.get(url)
    if r.status_code == 200:
        if r.json().get('ip_addr'):
            return r.json()['ip_addr']

    else:
        return '127.0.0.1'

async def fix_error(service, project, portal, error):
    data = {
        'date': time.ctime(),
        'project': project,
        'portal': portal,
        'error': error,
    }

    tab_name = 'ERRORS'
    await append_data_to_sheet_scope(service, ss_id, tab_name, data)

async def time_out_on(async_func, timeout=180, **kwargs):
    ts = random.randint(5, max_sec)
    print(f'Wait {ts} sec...')
    await asyncio.sleep(ts)

    service = kwargs['service']
    link = kwargs['link']
    df_mini_pattern = kwargs['df_mini_pattern']
    df_mini_criteria = kwargs['df_mini_criteria']
    ss_id = kwargs['ss_id']
    project = kwargs['project']

    try:
        status = await asyncio.wait_for(
            async_func(service, link, df_mini_pattern, df_mini_criteria, ss_id, project), timeout=timeout)

        if status:  # Если статус истинен
            await fix_error(service, project, link, str(status))
            return status

    except asyncio.TimeoutError as TE:
        await fix_error(service, project, link, f"TimeOut {TE}")
        print(f"Error TE: Задача была отменена из-за таймаута. {TE}")
        traceback.print_exc()
        return None

    except Exception as Ex:  # Обработка других исключений
        await fix_error(service, project, link, f"Error TOO Ex: {Ex}")
        print(f"Error TOO Ex: {Ex}")
        traceback.print_exc()
        return None

async def time_out_play(async_func, timeout=180, **kwargs):
    ts = random.randint(5, max_sec)
    print(f'Wait {ts} sec...')
    await asyncio.sleep(ts)

    service = kwargs['service']
    link = kwargs['link']
    df_mini_pattern = kwargs['df_mini_pattern']
    df_mini_criteria = kwargs['df_mini_criteria']
    ss_id = kwargs['ss_id']
    project = kwargs['project']

    playwright, browser, page = await get_playwright(link)
    if not page:
        return None, None, None

    status = None

    try:
        status = await asyncio.wait_for(
            async_func(service, link, df_mini_pattern, df_mini_criteria, ss_id, project, playwright, browser, page), timeout=timeout)

        if status:  # Если статус истинен
            await fix_error(service, project, link, str(status))

    except asyncio.TimeoutError as TE:
        await fix_error(service, project, link, f"TimeoutError {TE}")
        print(f"Error PLAY TE: Задача была отменена из-за таймаута. {TE}")
        traceback.print_exc()
        status = None

    except asyncio.CancelledError as CE:
        await fix_error(service, project, link, f"CancelledError {CE}")
        print(f"Error PLAY CE: Задача была отменена из-за таймаута. {CE}")
        traceback.print_exc()
        status = None

    except Exception as Ex:  # Обработка других исключений
        await fix_error(service, project, link, f"Error TOP Ex: {Ex}")
        print(f"Error PLAY Ex: Произошла ошибка: {Ex}")
        traceback.print_exc()
        status = None

    finally:
        if browser:
            await browser.close()
            await playwright.stop()
        print('-- Close browser and playwright is OK!')
        return status

async def time_out_sel(async_func, timeout=180, **kwargs):
    ts = random.randint(5, max_sec)
    print(f'Wait {ts} sec...')
    await asyncio.sleep(ts)

    service = kwargs['service']
    link = kwargs['link']
    df_mini_pattern = kwargs['df_mini_pattern']
    df_mini_criteria = kwargs['df_mini_criteria']
    ss_id = kwargs['ss_id']
    project = kwargs['project']

    driver = await get_selenium_proxy(link)
    status = None

    try:
        status = await asyncio.wait_for(
            async_func(service, link, df_mini_pattern, df_mini_criteria, ss_id, project, driver), timeout=timeout)

        if status:  # Если статус истинен
            await fix_error(service, project, link, str(status))

    except asyncio.TimeoutError as TE:
        await fix_error(service, project, link, f"TimeoutError {TE}")
        print(f"Error SEL TE: Задача была отменена из-за таймаута. {TE}")
        traceback.print_exc()
        status = None

    except asyncio.CancelledError as CE:
        await fix_error(service, project, link, f"CancelledError {CE}")
        print(f"Error SEL CE: Задача была отменена из-за таймаута. {CE}")
        traceback.print_exc()
        status = None

    except Exception as Ex:  # Обработка других исключений
        await fix_error(service, project, link, f"Error TOP Ex: {Ex}")
        print(f"Error SEL Ex: Произошла ошибка: {Ex}")
        traceback.print_exc()
        status = None

    finally:
        if driver:
            driver.quit()
        print('-- Close SEL is OK!')
        return status


async def get_articles(top_url):
    async def parse_read_count(text):
        # Извлечение числа прочтений с учетом формата с запятыми и суффиксом "K"
        match = re.search(r'(\d+(?:,\d+)?K?) прочтений?', text)
        if match:
            count = match.group(1).replace(',', '.')
            if 'K' in count:
                count = float(count.replace('K', '')) * 1000
            return int(count)
        return 0

    url = f'{top_url}?bookmark_desktop=true&tab=articles'

    response = requests.get(url)
    html_content = response.text

    # Создаем объект BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Пример: получение заголовка страницы
    title = soup.title
    print('Заголовок страницы:', title.text.strip())

    cards = soup.find_all('article', class_='desktop2--card-part-wrapper__cardPartWrapper-3S card-article')
    print('Len cards =', len(cards))

    if len(cards) == 0:
        cards = soup.find_all('article', {"aria-label":'Карточка этажа', "data-testid":"floor-image-card"})
        print('Len cards =', len(cards))

    if len(cards) == 0:
        cards = soup.find_all('article', {"data-testid":"floor-image-card"})
        print('Len cards =', len(cards))

    datas = []

    for card in cards:
        card_title = card.find('div', class_='desktop2--card-part-title__title-dF desktop2--card-part-title__l-1t').text
        print(card_title)

        numbers = card.find('div', class_='desktop2--meta__meta-3m').text.split('.')
        print(numbers)

        views = numbers[0]
        int_views = await parse_read_count(views)
        print(int_views)

        datas.append([card_title, int_views])

    df = pd.DataFrame(datas)
    df = df.sort_values(by=1, ascending=False).head(20).reset_index(drop=True)
    print(df)
    return df
