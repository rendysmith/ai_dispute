import os
import random
import time

import asyncio
import traceback

import requests
from dotenv import load_dotenv

from utils.constants import TABLES_LIST
from utils.gs_editor import append_data_to_sheet_scope
from utils.user_agent import get_playwright

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