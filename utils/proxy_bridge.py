import asyncio
import json
import random

import aiohttp
#import socks
#import socket
#from stem import Signal
#from stem.control import Controller

#import aiohttp
import requests
import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)
token_proxy = os.environ.get("TOKEN_PROXY")
login_proxy = os.environ.get("LOGIN_PROXY")
pass_proxy = os.environ.get("PASS_PROXY")

async def get_serviceid():
    url = 'https://api.proxy5.net/api/billing/invoices'
    headers = {
        'Authorization': f'Basic {token_proxy}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    response = requests.request('GET', url, headers=headers)
    r_json = response.json()
    serviceid = r_json[0]['serviceid']
    return serviceid

async def get_client_list():
    url = 'https://api.proxy5.net/api/clients'
    headers = {
        'Authorization': f'Basic {token_proxy}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    response = requests.request('GET', url, headers=headers)
    r_json = response.json()
    print(r_json)

async def get_iplist():
    """ typel  string
        IP list type http-ip or socks-ip or http-auth or ppr-http or ppr-socks.
        formatl  string
        IP list format csv or txt or json.
        id  string
        Service ID."""
    serviceid = await get_serviceid()
    url = f'https://api.proxy5.net/api/iplist/http-auth/json/{serviceid}'
    headers = {
        'Authorization': f'Basic {token_proxy}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    response = requests.request('GET', url, headers=headers)
    r_json = response.json()
    print(r_json)
    host_port = random.choice(r_json)
    print(host_port)
    return host_port

async def get_proxy_list():
    url = f'https://proxy5.net/api/getproxy/?format=json&type=http_auth&login={login_proxy}&password={pass_proxy}'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            text = await response.text()
            text = text.replace(',', '')
            print("Original text:", text)
            input()

            formatted_text = '[{}]'.format(text.strip().replace('},\n{', '}, {'))
            print("Formatted text:", formatted_text)

            try:
                data = json.loads(formatted_text)
                print(data)

            except json.JSONDecodeError as e:
                print("JSONDecodeError:", e)
                print("Formatted text that caused the error:", formatted_text)

async def change_setip(ip):
    url = f'https://proxy5.net/api/getproxy/?action=setip&login={login_proxy}&password={pass_proxy}&ip={ip}'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            text = response.text
            print(text)

async def proxy_tor_stem():
    # Устанавливаем SOCKS прокси для использования Tor
    socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, '127.0.0.1', 9050)
    socket.socket = socks.socksocket

    # Функция для смены выходной ноды Tor на указанную страну (США)
    def change_tor_exit_node(country_code):
        with Controller.from_port(port=9051) as controller:
            controller.authenticate()
            controller.signal(Signal.NEWNYM)

    # Пример запроса к example.com
    def make_tor_request(url):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response.text
            else:
                return f"Request failed with status code {response.status_code}"
        except requests.exceptions.RequestException as e:
            return f"Request failed: {e}"

    # Сменяем выходную ноду на США
    change_tor_exit_node('us')

    # Пример использования
    url = 'https://api.ipify.org?format=json'
    response = make_tor_request(url)
    print(response.join())

async def proxy_tor():
    proxies = {
        'http': 'socks5h://127.0.0.1:9050',
        'https': 'socks5h://127.0.0.1:9050'
    }

    # URL для получения IP-адреса в формате JSON
    url = 'https://api.ipify.org?format=json'

    # Выполнение запроса для проверки соединения через Tor
    result = requests.get(url, proxies=proxies)
    print(result.json())

#
#
# asyncio.run(proxy_tor())



