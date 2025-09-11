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
    #print(response.join())

async def proxy_tor():
    proxies = {
        'http': 'socks5h://127.0.0.1:9050',
        'https': 'socks5h://127.0.0.1:9050'
    }

    # URL для получения IP-адреса в формате JSON
    url = 'https://api.ipify.org?format=json'

    # Выполнение запроса для проверки соединения через Tor
    result = requests.get(url, proxies=proxies)
    #print(result.json())

async def main_proxy():
    host_port = await get_one_proxy()
    #print(host_port)
    input('OK!')


    # service = await get_serviceid()
    # print(service)

    proxy_list = await parse_data()
    for i in proxy_list:
        #print(i)
        ##print(i['host'])
        #print(i['port'])
        input()

    host_port = await get_iplist()
    #print(host_port)
    input()

    proxies = {
        'http': f'http://{login_proxy}:{pass_proxy}@{host_port}',
        'https': f'https://{login_proxy}:{pass_proxy}@{host_port}'
    }

    response = requests.get(url, headers=headers, proxies=proxies, timeout=10)

async def set_windows_proxy():
    import winreg
    host, port = await get_one_proxy()

    proxy = f"{host}:{port}"
    os.environ['http_proxy'] = f"http://{login_proxy}:{pass_proxy}@{proxy}"
    os.environ['https_proxy'] = f"https://{login_proxy}:{pass_proxy}@{proxy}"

    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        0, winreg.KEY_SET_VALUE
    )
    winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
    winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, proxy)
    winreg.CloseKey(key)

    # Обновление настроек прокси без перезагрузки
    #os.system('RunDll32.exe InetCpl.cpl,LaunchConnectionDialog')


if "__main__" in __name__:
    srv = asyncio.run(get_one_proxy())
    print(srv)



