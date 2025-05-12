import asyncio
import random

import requests

from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

from utils.gs_editor import pars_url
from utils.ai_module import generate_and_white
from utils.user_agent import gen_ua

import os
from dotenv import load_dotenv

current_date = datetime.now(timezone.utc)

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

login_aplaut = os.environ.get("LOGIN_APLAUT")
pass_aplaut = os.environ.get("PASS_APLAUT")

async def auth_aplout():
    login_url = 'https://app.aplaut.io/auth/users/sign_in'

    # Создание сессии
    session = requests.Session()

    # Получение страницы авторизации для извлечения CSRF-токена
    domen = 'https://aplaut.io'
    headers = await gen_ua(domen)
    response = session.get(login_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Извлечение CSRF-токена
    csrf_token = soup.find('input', {'name': 'authenticity_token'})['value']

    # Данные для авторизации
    payload = {
        'authenticity_token': csrf_token,
        'user[email]': login_aplaut,  # Замените на ваш email
        'user[password]': pass_aplaut  # Замените на ваш пароль
    }

    # Отправка POST-запроса для авторизации
    response = session.post(login_url, data=payload)

    # Проверка успешной авторизации
    if response.url == login_url:
        print("Ошибка авторизации.")
    else:
        print("Успешная авторизация!")
        return session, headers


async def check_aplout(service, link, pattern, criteria, ss_id, project, links=False):

    print("\n", link)
    if not links:
        links = await pars_url(service, ss_id, project)

    #scraper = cloudscraper.create_scraper()  # returns a requests.Session object
    session, headers = await auth_aplout()
    if not session:
        return 'Проблемы с авторизацией'

    #https://app.aplaut.io/b/api/reviews.json?filter=comments:eq:not_exists&page=1&sort=imported_at:desc
    link = 'https://app.aplaut.io/b/api/reviews.json'
    response = session.get(link, headers=headers)
    for block in response.json()['reviews']:
        url_answer = 'https://app.aplaut.io/b/reviews/' + block['id']

        if url_answer in links:
            print(f"Такой комментарий уже отмечен {url_answer}")
            continue

        if block['comments'] != []:
            print('Уже есть комментарий, пропускаем.')
            continue

        date_content = block['created_at']
        date = datetime.strptime(date_content, "%Y-%m-%dT%H:%M:%S.%f%z")
        formatted_date = date.strftime("%d.%m.%Y")

        if (current_date - date) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней. = {date}')
            continue

        author = block['author_name']
        feedback = block['body']

        await generate_and_white(service=service,
                                 url_answer=url_answer,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)


async def main_aplaut():
    from utils.gs_editor import get_service
    service = await get_service()
    url = 'https://app.aplaut.io/b/reviews/668b49b07e0e34001a4a2fb5'
    await check_aplout(service, url, 1,1,'1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w',1)

if "__main__" in __name__:
    asyncio.run(main_aplaut())

    #asyncio.run(main(url))



