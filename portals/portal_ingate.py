import asyncio
import os
from datetime import datetime

import aiohttp
import requests
from dotenv import load_dotenv
from requests import session

current_date = datetime.now()
record_date = current_date.strftime("%d.%m.%Y")

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

login = os.environ.get("LOGIN_INGATE")
password = os.environ.get("PASS_INGATE")

async def auth_ingate():
    login_url = "https://pntr.ingate.ru/api/client/login"
    headers = {
        "Content-Type": "application/json",
        "x-hostname": "pntr.ingate.ru"
    }

    login_data = {
        'email': login,
        'password': password,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(login_url, json=login_data, headers=headers) as response:
            # Проверка статуса ответа
            if response.status == 200:
                print("- Успешная авторизация")
                # Получение JWT токена из cookies
                jwt_token = response.cookies.get('_jwt1').value
                print("JWT токен:", jwt_token)
                return jwt_token
            else:
                print("- Ошибка авторизации:", response.status)
                error_response = await response.json()
                print(error_response)
                return None






async def check_ingate():
    url = "https://pntr.ingate.ru/api/client/v100/networks/940/reviews?orderBy=commentedAt&direction=desc&limit=50&offset=0&withAllCounts=false&isHidden=false"
    jwt_token = await auth_ingate()

    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",
        "Accept": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                print("Данные:", data)
            else:
                print("Ошибка доступа:", response.status)
                error_response = await response.json()
                print(error_response)

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",
        "Accept": "application/json",
        "Cookie": f"_jwt1={jwt_token}",  # Передаем токен как куку
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                print("Данные:", data)
            else:
                print("Ошибка доступа:", response.status)
                error_response = await response.json()
                print(error_response)
#asyncio.run(auth_ingate())
asyncio.run(check_ingate())
