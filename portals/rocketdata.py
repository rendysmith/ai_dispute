import asyncio
import os
from datetime import datetime

import aiohttp
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from utils.user_agent import extract_main_site, gen_ua

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

now = datetime.now()
days_ago = 3

email = os.environ.get("LOGIN_ROCKETDATA")
password = os.environ.get("PASS_ROCKETDATA")

async def start():
    async with aiohttp.ClientSession() as session:
        login_url = "https://go.rocketdata.io/auth/login"

        # Получение страницы входа
        async with session.get(login_url) as response:
            if response.status != 200:
                print(f"Ошибка при получении страницы входа: {response.status}")
                return None

            # Извлечение CSRF токена из куки
            csrf_token = None
            for cookie in session.cookie_jar:
                if cookie.key == "csrftoken":
                    csrf_token = cookie.value
                    break
            if not csrf_token:
                print("CSRF токен не найден в куки")
                return None

    input()






    # URL для POST запроса
    auth_url = "https://go.rocketdata.io/auth/login"
    api_url = 'https://go.rocketdata.io/op/api/v4/reviews/?ordering=-creation_date&per_page=50'

    # Данные для авторизации (замените на свои)
    data = {
        "email": email,
        "password": password
    }

    # Заголовки (возможно, нужно будет скопировать их из браузера)

    domen = await extract_main_site(auth_url)
    headers = await gen_ua(domen)

    # Создаем сессию
    session = requests.Session()

    response = session.post(auth_url, json=data, headers=headers, allow_redirects=False)

    # Проверяем результат
    print(response.status_code)
    print(response.text)
    print(response.headers)

    # Авторизация
    response = session.post(auth_url, json=data, headers=headers)
    print(response.text)

    # Проверка успешной авторизации
    if response.status_code == 200:
        # Используем сессию для запроса к API
        api_response = session.get(api_url)

        if api_response.status_code == 200:
            print("API ответ:", api_response.json())
        else:
            print(f"Ошибка API: {api_response.status_code}")
    else:
        print(f"Ошибка авторизации: {response.status_code}")

asyncio.run(start())
input()


async def rocketdata_login():
    """Асинхронная функция для входа в RocketData.

    Args:
        email: Email адрес пользователя.
        password: Пароль пользователя.

    Returns:
        Авторизированная сессия aiohttp.ClientSession, если вход успешный.
        None, если вход не удался.
    """

    async with aiohttp.ClientSession() as session:
        # Получение CSRF токена (если требуется)
        login_url = "https://go.rocketdata.io/auth/login" # Замените на правильный URL входа

        domen = await extract_main_site(login_url)
        headers = await gen_ua(domen)

        async with session.get(login_url, headers=headers) as response:
            if response.status != 200:
                print(f"Ошибка при получении страницы входа: {response.status}")
                return None

            soup = BeautifulSoup(await response.text(), "html.parser")
            print(soup)
            input()

            # Ищем CSRF токен (если он используется на сайте)
            csrf_token = None
            csrf_input = soup.find("input", attrs={"name": "csrf_token"})  # Замените на правильное имя поля, если отличается
            if csrf_input:
                csrf_token = csrf_input["value"]

        # Отправка данных для входа
        payload = {
            "email": email,
            "password": password,
            "rememberMe": "on",  # Если нужно запомнить сессию
        }

        if csrf_token:
            payload["csrf_token"] = csrf_token

        async with session.post(login_url, data=payload) as response:
            if response.status == 200:
                 # Проверяем редирект или наличие специального куки для авторизации
                if "location" in response.headers or session.cookie_jar._cookies["rocketdata.io"].get("/"):
                    print("Вход успешен!")
                    return session # Возвращаем авторизированную сессию

                else:
                    print("Вход не удался. Проверьте email и пароль.")
                    return None

            elif response.status == 401:
                print(f"Неверный email или пароль.")
                return None

            else:
                print(f"Ошибка при входе: {response.status}")
                return None


async def check_rocketdata():
    url = 'https://go.rocketdata.io/op/api/v4/reviews/?ordering=-creation_date&per_page=50'
    session = await rocketdata_login()
    async with session.get(url) as response:
        if response.status == 200:
            r_json = await response.json()

            print(r_json)


async def main_rocketdata():
    await check_rocketdata()



if __name__ == '__main__':
    asyncio.run(main_rocketdata())
    print('The End!')
