import asyncio
import random


import requests
from Cython.Compiler.Nodes import reset_exception_utility_code
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

from utils.gs_editor import pars_url
from utils.ai_module import generate_and_white
from utils.user_agent import gen_ua
import textwrap

from utils.user_agent import get_selenium

import os
from dotenv import load_dotenv

current_date = datetime.now()

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
    response = session.get(login_url)
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
        return session


async def check_irecommend(service, link, pattern, criteria, ss_id, project):
    ts = random.randint(5, max_sec)
    print(f"Wait {ts} sec.")
    await asyncio.sleep(ts)

    print("\n", link)
    links = await pars_url(service, ss_id, project)

    domen = "https://irecommend.ru"
    headers = await gen_ua(domen)

    #scraper = cloudscraper.create_scraper()  # returns a requests.Session object
    response = requests.get(link, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    #print(soup)

    try:
        top_block = soup.find("div", {"class": "headerWithMenu margin30"})
        print(f'Получение главной темы на основании комментов.')
        top_url = domen + top_block.find("a")['href'] + "?new=1"
        #print(top_url)

    except AttributeError as AE:
        print('!!!(irecommend) Возможно сработала защита Cloudflore...')
        #checkbox = soup.find('input', {'type': 'checkbox'})
        return AE

    except Exception as Ex:
        return Ex

    response = requests.get(top_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    blocks = soup.find_all("div", {"data-photos-count": '0', "data-type": "1"})
    print(len(blocks))

    for block in blocks:
        url_n = block.find("a", class_='reviewTextSnippet')['href']
        url_answer = domen + url_n
        if url_answer in links:
            print('Отзыв уже есть в таблице')
            continue

        try:
            date = block.find("div", {"class": "created"}).text
            target_date = datetime.strptime(date, "%d.%m.%Y")

        except:
            date_1 = block.find("div", {"class": "created"})
            date = date_1.find("span", {"class": "date-created"}).text
            target_date = datetime.strptime(date, "%d.%m.%Y")

        if (current_date - target_date) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней = {date}.')
            continue

        author = block.find("div", class_="authorName").text

        title = block.find("div", {"class": "reviewTitle"}).text
        title_txt = block.find("span", {"class": "reviewTeaserText"}).text

        feedback = f"""
        {title}
        {title_txt}
        """
        feedback = textwrap.dedent(feedback)
        #print(feedback)

        formatted_date = date

        #await generate_and_white(service, url_answer, author, formatted_date, prompt)
        await generate_and_white(service=service,
                                 url_answer=url_answer,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)

    return True

# async def check_irecommend_selenium(service, link, pattern, criteria, ss_id, project):
#     ts = random.randint(5, 30)
#     print(f"Wait {ts} sec.")
#     await asyncio.sleep(ts)
#
#     print("\n", link)
#     links = await pars_url(service, ss_id, project)
#
#     driver = await get_selenium(link)
#
#     scraper = cloudscraper.create_scraper()  # returns a requests.Session object
#     response = scraper.get(link, headers=headers)
#     soup = BeautifulSoup(response.text, 'html.parser')
#     #print(soup)
#
#     top_block = soup.find("div", {"class": "headerWithMenu margin30"})
#     print('Получение главной темы на основании комментов')
#     top_url = domen + top_block.find("a")['href'] + "?new=1"
#     print(top_url)
#
#     response = requests.get(top_url, headers=headers)
#     soup = BeautifulSoup(response.text, 'html.parser')
#
#     blocks = soup.find_all("div", {"data-photos-count": '0', "data-type": "1"})
#     print(len(blocks))
#
#     for block in blocks:
#         url_n = block.find("a", class_='reviewTextSnippet')['href']
#         url_answer = domen + url_n
#         if url_answer in links:
#             print('Отзыв уже есть в таблице')
#             continue
#
#         try:
#             date = block.find("div", {"class": "created"}).text
#             target_date = datetime.strptime(date, "%d.%m.%Y")
#
#         except:
#             date_1 = block.find("div", {"class": "created"})
#             date = date_1.find("span", {"class": "date-created"}).text
#             target_date = datetime.strptime(date, "%d.%m.%Y")
#
#         if (current_date - target_date) > timedelta(days=days_ago):
#             print(f'--- Отзыв старше {days_ago} дней = {date}.')
#             continue
#
#         author = block.find("div", class_="authorName").text
#
#         title = block.find("div", {"class": "reviewTitle"}).text
#         title_txt = block.find("span", {"class": "reviewTeaserText"}).text
#
#         feedback = f"""
#         {title}
#         {title_txt}
#         """
#         feedback = textwrap.dedent(feedback)
#         print(feedback)
#
#         formatted_date = date
#
#         #await generate_and_white(service, url_answer, author, formatted_date, prompt)
#         await generate_and_white(service=service,
#                                  url_answer=url_answer,
#                                  author=author,
#                                  formatted_date=formatted_date,
#                                  ss_id=ss_id,
#                                  project=project,
#                                  feedback=feedback,
#                                  pattern=pattern,
#                                  criteria=criteria)


async def main(url):
    from utils.gs_editor import get_service
    service = await get_service()
    await check_irecommend(service, url, 1,1,'1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w','Кордиант')

if "__main__" in __name__:
    url = "https://irecommend.ru/content/samye-nadezhnye-shiny-iz-nedorogikh"

    asyncio.run(auth_aplout())

    #asyncio.run(main(url))



