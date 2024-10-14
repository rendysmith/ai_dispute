import asyncio
import os

from datetime import datetime, timedelta
import random

import aiohttp

from dotenv import load_dotenv

from utils.gs_editor import get_service, pars_url
from utils.ai_module import generate_and_white

current_date = datetime.now()

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

email = os.environ.get("LOGIN_ROCKETDATA")
password = os.environ.get("PASS_ROCKETDATA")

async def check_rocketdata(service, link, pattern, criteria, ss_id, project):
    print(link)
    ts = random.randint(5, max_sec)
    print(f'Wait {ts} sec...')
    await asyncio.sleep(ts)

    async with aiohttp.ClientSession() as session:

        login_url = "https://go.rocketdata.io/op/api/user/login/"
        #domen = await extract_main_site(login_url)
        #headers = await gen_ua(domen)

        payload = {
            "email": email,
            "password": password,
            "remember_me": False
        }

        # Получение страницы входа
        async with session.post(login_url, json=payload) as response:
            if response.status != 200:
                if response.status == 400:
                    print('400:')

                else:
                    print(f"Ошибка при получении страницы входа: {response.status}")
                    return None

            else:
                print('Connect OK!')

        url = 'https://go.rocketdata.io/op/api/v4/reviews/?ordering=-creation_date&per_page=50'
        async with session.get(url) as response:
            if response.status != 200:
                print(f"Ошибка при получении страницы входа: {response.status}")
                return None

            else:
                r_json = await response.json()
                print(response.status)

    links = await pars_url(service, ss_id, project)

    for i in r_json['results']:
        company_answer = i['children']
        if company_answer:
            continue

        date_content = i['created_in_catalog']
        date = datetime.strptime(date_content, "%Y-%m-%dT%H:%M:%S.%fZ")
        date = date.replace(tzinfo=None)  # offset-naive

        formatted_date = date.strftime("%d.%m.%Y")

        if (current_date - date) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней. = {date}')
            return

        url_answer = i['id']
        print(url_answer)
        if url_answer in links:
            print("Такой комментарий уже отмечен")
            continue

        author = i['author']
        print(author)
        feedback = i['comment']
        print(feedback)

        await generate_and_white(service=service,
                                 url_answer=url_answer,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)


async def main_rocketdata():
    service = await get_service()

    url = '1'
    await check_rocketdata(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", 1)



if __name__ == '__main__':
    asyncio.run(main_rocketdata())
    print('The End!')
