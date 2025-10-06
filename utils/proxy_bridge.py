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

import json
import random
import requests
import time
from typing import Dict, Optional, List

from utils.user_agent import get_soup

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

async def send_request_via_flareprox(
        target_url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[str] = None,
        create_if_needed: bool = True,
        num_creation_attempts: int = 1
) -> Optional[requests.Response]:
    """
    Sends an HTTP request to the target URL via a FlareProx endpoint.

    Args:
        config_file (str): Path to the FlareProx configuration file.
        target_url (str): The URL to which the request should be proxied.
        method (str): The HTTP method for the request (e.g., GET, POST, PUT, DELETE).
        headers (Optional[Dict[str, str]]): Optional headers to include in the request.
        data (Optional[str]): Optional body data for the request (for POST, PUT, etc.).
        create_if_needed (bool): If True, attempts to create a new proxy endpoint
                                 if no active endpoints are found.
        num_creation_attempts (int): Number of times to try creating a proxy endpoint
                                     if creation is needed and fails initially.

    Returns:
        Optional[requests.Response]: The response object from the target URL if successful,
                                     otherwise None.
    """

    from utils.flareprox import FlareProxError, FlareProx

    config_file = "flareprox.json"

    try:
        # 1. Инициализировать FlareProx
        flareprox = FlareProx(config_file=config_file)

        # 2. Проверить, настроено ли
        if not flareprox.is_configured:
            print(f"FlareProx не настроен. Проверьте файл: {config_file}")
            return None

        # 3. Синхронизировать/получить список эндпоинтов
        endpoints = flareprox.sync_endpoints()

        # 4. Если нет эндпоинтов, и create_if_needed=True, создать один
        if not endpoints and create_if_needed:
            print("Активных эндпоинтов FlareProx не найдено. Создаю новый...")
            creation_success = False
            for attempt in range(num_creation_attempts):
                try:
                    result = flareprox.create_proxies(count=1)
                    if result.get("created") and len(result["created"]) > 0:
                        print(f"Новый эндпоинт FlareProx успешно создан: {result['created'][0]['url']}")
                        creation_success = True
                        # Обновляем список после создания
                        endpoints = flareprox.sync_endpoints()
                        break
                    else:
                        print(f"Попытка создания эндпоинта #{attempt + 1} не удалась. Ошибка в ответе API.")
                except FlareProxError as e:
                    print(f"Ошибка при создании эндпоинта (попытка #{attempt + 1}): {e}")
                    if attempt < num_creation_attempts - 1:
                        print("Повторная попытка через 5 секунд...")
                        time.sleep(5)
                except Exception as e:
                    print(f"Неожиданная ошибка при создании эндпоинта (попытка #{attempt + 1}): {e}")
                    if attempt < num_creation_attempts - 1:
                        time.sleep(5)

            if not creation_success:
                print("Не удалось создать новый эндпоинт FlareProx после нескольких попыток.")
                return None

        # 5. Если после синхронизации или создания всё ещё нет эндпоинтов
        if not endpoints:
            print("Нет доступных эндпоинтов FlareProx для использования.")
            return None

        # 6. Выбрать случайный эндпоинт
        chosen_endpoint = random.choice(endpoints)
        flareprox_url = chosen_endpoint['url']
        print(f"Использую эндпоинт FlareProx: {flareprox_url}")

        # 7. Построить URL для запроса к FlareProx (целевой URL в параметрах)
        proxy_request_url = f"{flareprox_url}?url={target_url}"

        # 8. Подготовить заголовки (FlareProx сам обработает их)
        request_headers = headers or {}
        # Важно: не перезаписывать Host, если он был передан, FlareProx сам его установит
        if 'Host' in request_headers:
            del request_headers['Host']

        # 9. Выполнить запрос через FlareProx
        print(f"Отправляю {method} запрос к {target_url} через {flareprox_url}")
        response = requests.request(
            method=method,
            url=proxy_request_url,
            headers=request_headers,
            data=data,
            timeout=60  # Установите таймаут по вашему усмотрению
        )

        print(f"Получен ответ от {target_url} через FlareProx: {response.status_code}")
        return response

    except requests.RequestException as e:
        print(f"Ошибка при выполнении запроса через FlareProx: {e}")
        return None
    except FlareProxError as e:
        print(f"Ошибка FlareProx: {e}")
        return None
    except Exception as e:
        print(f"Неожиданная ошибка в send_request_via_flareprox: {e}")
        return None


if "__main__" in __name__:
    soup = asyncio.run(get_soup("https://2gis.ru/ufa/firm/70000001046160277", proxy=False))
    print(soup)




