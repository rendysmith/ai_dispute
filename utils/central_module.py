import base64
import os
import random
import re
import time

import asyncio
import traceback
from datetime import datetime

import pandas as pd
import requests
from requests.auth import HTTPBasicAuth

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from sqlalchemy.util import await_only


from utils.constants import TABLES_LIST
from utils.gs_editor import append_data_to_sheet_scope, read_table_id, append_data_to_sheet_cell
from utils.user_agent import get_playwright, get_selenium_proxy

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

now = datetime.now()
record_date = now.strftime("%d.%m.%Y")

token_proxy = os.environ.get("TOKEN_PROXY")
id_proxy = os.environ.get("ID_PROXY")

email_proxy = os.environ.get("EMAIL_PROXY")
password_proxy = os.environ.get("PASSWORD_PROXY")

max_sec = int(os.environ.get("MAX_SEC"))
ss_id = TABLES_LIST['zoom']

auth_username = os.environ.get("HOST_USERNAME")
auth_password = os.environ.get("HOST_PASSWORD")
auth = HTTPBasicAuth(auth_username, auth_password)

async def get_local_ip():
    try:
        url = 'https://api.myip.com/'
        r = requests.get(url)
        if r.status_code == 200:
            if r.json().get('ip'):
                return r.json()['ip']

            else:
                return '127.0.0.1'

    except requests.exceptions.ConnectionError as CE:
        url = 'https://api.ipify.org?format=json'
        r = requests.get(url)
        if r.status_code == 200:
            if r.json().get('ip'):
                return r.json()['ip']

            else:
                return '127.0.0.1'

    except:
        url = 'https://ifconfig.me/all.json'
        r = requests.get(url)
        if r.status_code == 200:
            if r.json().get('ip_addr'):
                return r.json()['ip_addr']

        else:
            return '127.0.0.1'

async def get_hpo():
    local_ip = await get_local_ip()
    if '176.124.192' in local_ip:
        headless = True
        proxy_on = True
        only_text = False

    else:
        print(f'local_ip: {local_ip}')
        headless = False
        proxy_on = False
        only_text = False

    return headless, proxy_on, only_text

async def get_proxy_token(email: str, password: str):
    """
    Создаёт заголовок Authorization для Basic аутентификации.

    :param email: Электронная почта пользователя.
    :param password: Пароль пользователя.
    :return: Словарь с заголовком Authorization.
    """
    credentials = f"{email}|{password}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    return encoded_credentials

async def get_serviceid(token_proxy):
    url = 'https://api.proxy5.net/api/billing/invoices'
    headers = {
        'Authorization': f'Basic {token_proxy}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    response = requests.request('GET', url, headers=headers)
    r_json = response.json()

    r_json.reverse()

    for rj in r_json:
        if rj['serviceid']:
            serviceid = rj['serviceid']
            return serviceid

def get_local_ip_sync():
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

def proxy_status_sync():
    proxy_action = asyncio.run(get_api_service())
    return proxy_action['status']

async def get_api_service():
    token_proxy = await get_proxy_token(email_proxy, password_proxy)
    id_proxy = await get_serviceid(token_proxy)

    url = f'https://api.proxy5.net/api/service/{id_proxy}'
    headers = {
        'Authorization': f'Basic {token_proxy}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    response = requests.get(url, headers=headers)
    #print(response)
    r_json = response.json()
    print(r_json)
    print(f'- Binded IP: {r_json.get("bindedip")}')
    return r_json

async def proxy_status():
    proxy_action = await get_api_service()
    return proxy_action['status']

async def wait_for_portal():
    """
    Функция ожидания портала.
    Returns: random secs.
    """
    ts = random.randint(5, max_sec)
    print(f'...Wait {ts} sec...')
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

    headless, proxy_on, only_text = await get_hpo()
    driver = await get_selenium_proxy(link, proxy=proxy_on)
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

async def rec_data(service, date_create, url_answer, first_author, prompt_trend_gone, comments, text, sheet_id, worksheet_name):
    from utils.ai_module import get_answer_ai

    """
    Функция для BA - определение тренда.
    Args:
        service:
        date_create:
        url_answer:
        first_author:
        prompt_trend_gone:
        comments:
        text:
        sheet_id:
        worksheet_name:

    Returns: bool

    """
    prompt = prompt_trend_gone.format(chat_list=comments, text=text)
    result = await get_answer_ai(auth, prompt)
    print("result AI:", result)

    if result == 'True':
        data = {
            'record_date': record_date,
            'date_create': date_create,
            'portal': url_answer,
            'author': first_author,
            'feedback': text}

        await append_data_to_sheet_scope(service, sheet_id, worksheet_name, data)
        print('Rec data...')

async def rec_count(service, ss_id, project):
    df = await read_table_id(service, ss_id, "logs")

    try:
        idx = df[df['service_name'] == project].index[0]
        count = df.loc[idx, 'recorded']
        date = df.loc[idx, 'date']

        print(idx, date, count)

        if count == "":
            rec_count = 1

        # elif date != record_date:
        #     rec_count = 1
        #     await append_data_to_sheet_cell(service, ss_id, 'logs', 'date', idx + 2, record_date)

        else:
            rec_count = int(count) + 1

        print(idx, rec_count)
        await append_data_to_sheet_cell(service, ss_id, 'logs', 'recorded', idx + 2, rec_count)

    except Exception as Ex:
        print(f'--- Error <{project}> rec_count. {Ex}')




if "__main__" == __name__:
    from utils.gs_editor import get_service
    service = asyncio.run(get_service())
    asyncio.run(rec_count(service, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", "ya_maps_НовикомБанк"))