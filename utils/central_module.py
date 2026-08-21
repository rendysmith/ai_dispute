import os
import random

import asyncio

import requests
from dotenv import load_dotenv

core_path = os.path.dirname(os.path.dirname(__file__))
dotenv_path = os.path.join(core_path, '.env')
load_dotenv(dotenv_path)

max_sec = int(os.environ.get("MAX_SEC"))


async def get_local_ip():
    """Функция для получения IP адреса текущего сервера"""

    try:
        url = 'https://api.myip.com/'
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            if r.json().get('ip'):
                return r.json()['ip']

            else:
                return '127.0.0.1'

        else:
            r.raise_for_status()

    except requests.exceptions.ConnectionError as CE:
        url = 'https://api.ipify.org?format=json'
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            if r.json().get('ip'):
                return r.json()['ip']

            else:
                return '127.0.0.1'

        else:
            r.raise_for_status()

    except Exception as Ex:
        url = 'https://ifconfig.me/all.json'
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            if r.json().get('ip_addr'):
                return r.json()['ip_addr']

            else:
                return '127.0.0.1'

        else:
            r.raise_for_status()

    else:
        return '127.0.0.1'


async def get_hpo():
    local_ip = await get_local_ip()
    if '176.124' in local_ip:
        headless = True
        proxy_on = True
        only_text = False

    else:
        print(f'local_ip: {local_ip}')
        headless = False
        proxy_on = False
        only_text = False

    return headless, proxy_on, only_text


async def wait_for_portal():
    """
    Функция ожидания портала.
    Returns: random secs.
    """
    ts = random.randint(5, max_sec)
    print(f'...Wait {ts} sec...')
    await asyncio.sleep(ts)
