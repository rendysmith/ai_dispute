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

    # serviceid = await get_serviceid()
    # url = f'https://api.proxy5.net/api/iplist/http-auth/json/{serviceid}'
    # headers = {
    #     'Authorization': f'Basic {token_proxy}',
    #     'Content-Type': 'application/json',
    #     'Accept': 'application/json'
    # }
    #
    # response = requests.request('GET', url, headers=headers)
    # r_json = response.json()
    # if r_json.get('error'):
    #     return None

    r_json = await parse_data()
    #print(r_json)
    host_port_dict = random.choice(r_json)
    #print(host_port)
    return f"{host_port_dict['host']}:{host_port_dict['port']}"

async def get_proxy_list():
    #url = f'https://proxy5.net/api/getproxy/?format=json&type=http_auth&login={login_proxy}&password={pass_proxy}'
    url = f'https://proxy5.net/api/getproxy/?format=json&type=http_auth&login={login_proxy}&password={pass_proxy}'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            text = await response.text()
            text = text.replace(',', '')
            #print("Original text:", text)

            formatted_text = '[{}]'.format(text.strip().replace('},\n{', '}, {'))
            #print("Formatted text:", formatted_text)

            try:
                data = json.loads(formatted_text)
                print(type(data))
                return data

            except json.JSONDecodeError as e:
                print("JSONDecodeError:", e)
                print("Formatted text that caused the error:", formatted_text)

async def parse_data():
    url = f'https://proxy5.net/api/getproxy/?format=json&type=http_auth&login={login_proxy}&password={pass_proxy}'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data_string = await response.text()

            # Разделяем строку на отдельные строки и удаляем пустые строки
            lines = [line.strip() for line in data_string.split('\n') if line.strip()]

            # Создаем список для хранения результатов
            result = []

            # Асинхронно обрабатываем каждую строку
            async def process_line(line):
                # Удаляем запятую в конце строки, если она есть
                line = line.rstrip(',')
                try:
                    # Пытаемся распарсить JSON из строки
                    data = json.loads(line)
                    return data
                except json.JSONDecodeError:
                    # Если строка не является валидным JSON, выводим ошибку
                    print(f"Ошибка при разборе строки: {line}")
                    return None

            # Создаем и запускаем задачи для каждой строки
            tasks = [asyncio.create_task(process_line(line)) for line in lines]

            # Ожидаем выполнения всех задач
            processed_data = await asyncio.gather(*tasks)

            # Фильтруем None значения (строки с ошибками) и добавляем в результат
            result = [item for item in processed_data if item is not None]

            return result

async def get_one_proxy():
    url = f'https://proxy5.net/api/getproxy/?r=1&format=txt&type=http_auth&login={login_proxy}&password={pass_proxy}'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            one_proxy = await response.text()
            data = one_proxy.split(':')
            #print(type(data))
            print('Proxy', data)
            return data[0], data[1]

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

async def main_proxy():
    host_port = await get_one_proxy()
    print(host_port)
    input('OK!')


    # service = await get_serviceid()
    # print(service)

    proxy_list = await parse_data()
    for i in proxy_list:
        print(i)
        print(i['host'])
        print(i['port'])
        input()

    host_port = await get_iplist()
    print(host_port)
    input()

    proxies = {
        'http': f'http://{login_proxy}:{pass_proxy}@{host_port}',
        'https': f'https://{login_proxy}:{pass_proxy}@{host_port}'
    }

    response = requests.get(url, headers=headers, proxies=proxies, timeout=10)


if "__main__" in __name__:
    asyncio.run(main_proxy())



