import asyncio
import os
import time
from datetime import datetime
from pprint import pprint

import aiohttp

from dotenv import load_dotenv

from utils.ai_module import generate_and_white
from utils.gs_editor import pars_url

current_date = datetime.now()
record_date = current_date.strftime("%d.%m.%Y")

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

login = os.environ.get("LOGIN_INGATE")
password = os.environ.get("PASS_INGATE")

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

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
                #print("JWT токен:", jwt_token)
                return jwt_token

            else:
                print("- Ошибка авторизации:", response.status)
                error_response = await response.json()
                print(error_response)
                return None

async def check_ingate(service, url, pattern, criteria, ss_id, project, links=False):
    url = "https://pntr.ingate.ru/api/client/v100/networks/940/reviews"
    jwt_token = await auth_ingate()

    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "DNT": "1",
        "Host": "pntr.ingate.ru",
        "Referer": "https://pntr.ingate.ru/940/feedback",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "TE": "trailers",
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",
        "x-hostname": "pntr.ingate.ru",
        "Cookie": f"_jwt1={jwt_token}"
    }

    params = {
        "orderBy": "commentedAt",
        "direction": "desc",
        "limit": 50,
        "offset": 0,
        "withAllCounts": "false",
        "isHidden": "false",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                data = await response.json()

            else:
                print("Ошибка доступа:", response.status)
                error_response = await response.json()
                print(error_response)
                return

    #pprint(data)

    if not links:
        links = await pars_url(service, ss_id, project)

    for block in data['reviews']:
        if block['replyText']: #если есть ответ компании
            continue

        date = block['commentedAt']
        date_obj = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ")
        date_timestamp = date_obj.timestamp()

        if time.time() - date_timestamp >=  days_ago * 24 * 3600:
            print(f'--- Комментарий больше {days_ago} дней.')
            return

        url_answer = block['meta']['providerLink']
        if url_answer in links:
            print('Такой комментарий уже есть в списке')
            continue

        author = block['authorName']
        feedback = block['commentText']

        formatted_date = date_obj.strftime('%d.%m.%Y')
        await generate_and_white(service=service,
                                 url_answer=url_answer,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)




if __name__ == '__main__':
    asyncio.run(check_ingate())
