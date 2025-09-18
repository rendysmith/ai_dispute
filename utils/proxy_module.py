import json
import os

import aiohttp
import requests
import asyncio
from bs4 import BeautifulSoup

from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)
#token_proxy = os.environ.get("TOKEN_PROXY")
login_proxy = os.environ.get("LOGIN_PROXY")
pass_proxy = os.environ.get("PASS_PROXY")

async def get_cookies_proxy5():
    login_url = "https://proxy5.net/user/index.php?rp=/login"

    from utils.user_agent import gen_ua
    headers = await gen_ua(login_url)

    headers = {
        "Host": "proxy5.net",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:142.0) Gecko/20100101 Firefox/142.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": "https://proxy5.net/user/clientarea.php?action=productdetails&id=13068",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Priority": "u=0, i",
        "TE": "trailers",
    }

    with requests.Session() as s:
        r = s.get(login_url, headers=headers)
        soup = BeautifulSoup(r.text, "html.parser")
        print(soup)

        scripts = soup.find_all("script")
        for script in scripts:
            print(script)


        print(token)

        data = {
            "token": token,  # лучше получить динамически
            "username": login_proxy,
            "password": pass_proxy,
            "rememberme": "on"
        }

        r = s.post(login_url, data=data)
        r.raise_for_status()
        return s.cookies.get_dict()  # словарь cookies

async def get_client_list():
    url = 'https://api.proxy5.net/api/clients'
    headers = {
        'Authorization': f'Basic {token_proxy}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    response = requests.request('GET', url, headers=headers)
    r_json = response.json()
    #print(r_json)

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
                #print(type(data))
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
    url = f'https://proxy5.net/api/getproxy/?r=1&format=json&type=https_auth&login={login_proxy}&password={pass_proxy}&hideloginpass=1'

    headers = {
        "Host": "proxy5.net",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:142.0) Gecko/20100101 Firefox/142.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": "https://proxy5.net/user/clientarea.php?action=productdetails&id=24422",
        "DNT": "1",
        "Connection": "keep-alive",
        "Cookie": "cf_clearance=Zo3Xxj9MN.YR2paOH_v5nbnFTXD3A9A6SIhcVWNHg1g-1758169460-1.2.1.1-hNuPNp6_s0fLv52E1qxPpZCAIiidZmscob0sSvCHFIxlTkgLtE2tldQkN7j8TECoGbRsar2SQdY5wGfufzrYAVtlYxfAD7B9iyaTOvcoUaMl8DBbrQSZT.zrc3MgkZty9zoP7jxz3l8yD0NWTmJ5rs3SsURctWJNAdIMzwywX4BJekzkL7k.vDgnusGiCbmZ2rYRDPSm9ktXoOD5tYV.sM0hmYqWEUGlxAjCK1eAYoys9egcCavRif62FoDm6KAM; _ga_2ZGKN4M0P5=GS2.1.s1758169460$o20$g1$t1758169995$j60$l0$h0; _ga=GA1.1.400365736.1750062339; _ym_uid=1750062358756211370; _ym_d=1750062358; WHMCSlogin_auth_tk=b2gvbHo5UU92MDU5QmcxTTZmV055Tk9leXcvQm9SUEh0YnJEYmVBSit4VnhUZUVxNldBdDJMR0QyRmVsdFFoTEUyUW1DWnhESk4zT21HbitUN0tVWEllakVwbDdETkpIRzBwbzd4MmF0TTRueEgzakIxeTM0WDk4aEdINk9BSWlxRHVMOThIUjVpelBXVTZ5MW1MdVc4UDRoM2FxMXBGcXpFWUJ6MVAySDM3VWFlWnNjM0Z5WTdGMWIvZFdicDVIQkZYV0hBVzJqWGdJWGl0bVgvZXQwTXBtK2NpQ1owZFRjb0tHSENkdEt4SDJtQ2g0VWFvdCsvYlFDQ1pHMmUvbWJQRTBxLytCb2gwSjdXa0xncHhrdGRFZ3hiZ0ZrMEFod1FKQXFLakhmREI0d24zMURkREhld2Nwa0dTcHh1YVVGVUljTTFXejBuY0kwdDVGM25SdzZrRmdNYU5sY3FRU3hINTVBQWswRDNjZVJBczdKMlBMTm1xMEtXY253LzM0bWxFbGpsSHZ5UWJWYjc5OFBPVVJzdGp4UExiWjlyOVVQWUdlU1E9PQ%3D%3D; _gcl_au=1.1.647490963.1757908712.772562712.1758104130.1758104131; _ym_isad=2; _ym_visorc=w; WHMCSy551iLvnhYt7=cot4s44n6t6lm3cpg1l2tuj88d",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Priority": "u=0, i",
        "TE": "trailers",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            one_json = await response.text()
            print(one_json)
            # one_json = json.loads(one_text)
            # print(type(one_json))
            # print(one_json)
            #return one_json['host'], one_json['port']

async def change_setip(ip):
    print('Change action IP')
    url = f'https://proxy5.net/api/getproxy/?action=setip&login={login_proxy}&password={pass_proxy}&ip={ip}'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            text = response.text
            #print(text)

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


if "__main__" in __name__:
    srv = asyncio.run(get_one_proxy())
    input(srv)

    # srv = asyncio.run(get_cookies_proxy5())
    # print(srv)