import asyncio
import json
from datetime import datetime, timedelta

import aiohttp
import requests
from bs4 import BeautifulSoup

from utils.gs_editor import get_service

import base64
import hashlib
import os, re

import os
import requests
from urllib.parse import urlencode, parse_qs
from time import sleep


from dotenv import load_dotenv

now = datetime.now()
current_date = now

now_month = now.month

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

login_proxy = os.environ.get("LOGIN_PROXY")
pass_proxy = os.environ.get("PASS_PROXY")

access_token = os.environ.get("VK_ACCESS_TOKEN")
#access_token = 'vk1.a.eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzaWQiOiJNV0ZoTkRobU5EWmhaamRsWVRZek5UTXhOVFpoT0dFdyIsImhhc2giOiI0MmJlNzA4ZDUxOWM4NGRjIiwiZXhwIjoxNzMxMzQ3OTgzfQ.nG4avYppaXPUYN-OOnlYvYraUbRR82RiPbUkkcqjm0Q'
client_id = os.environ.get("VK_CLIENT_ID")
client_secret = os.environ.get("VK_SECRET")
redirect_uri = 'https://sidorinlab.ru'
scope = 'wall'
state = '123456'

async def extract_wall_ids(url):
    match = re.search(r'wall-?(\d+)_(\d+)', url)  # '?' делает дефис опциональным
    if match:
        group_id = '-' + match.group(1)
        post_id = match.group(2)
        print(group_id, post_id)
        return group_id, post_id

    return None, None

async def get_token():
    """
     Получает токен доступа ВКонтакте через authorization code flow.

     Args:
         client_id (str): ID приложения ВКонтакте
         client_secret (str): Секретный ключ приложения ВКонтакте
         redirect_uri (str): Redirect URI, указанный в настройках приложения
         scope (str): Запрашиваемые права доступа (через запятую)

     Returns:
         str: Токен доступа
     """

    # Шаг 1: Получаем authorization code
    auth_url = (
        f"https://oauth.vk.com/authorize?client_id={client_id}&"
        f"redirect_uri={redirect_uri}&response_type=code&scope={scope}"
    )

    print(auth_url)

    # Делаем GET-запрос на auth_url
    response = requests.get(auth_url)

    # Ищем URL кнопки "Разрешить" и нажимаем ее
    allow_button_url = response.text.split('href="')[1].split('"')[0]
    response = requests.get(allow_button_url)

    # Извлекаем код авторизации из URL-параметров
    auth_code = parse_qs(response.url.split("?")[1])['code'][0]

    # Шаг 2: Обменять auth code на access token
    token_url = "https://oauth.vk.com/access_token"
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "code": auth_code
    }

    response = requests.post(token_url, params=params)
    data = response.json()

    if "access_token" in data:
        return data["access_token"]
    else:
        raise Exception(f"Ошибка получения токена: {data['error_description']}")

async def get_code():
    # Генерация случайной строки длиной от 43 до 128 символов (code_verifier)
    code_verifier = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8').rstrip('=')
    print(code_verifier)

    # Вычисляем SHA-256 от code_verifier
    code_challenge = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    print(code_challenge)

    # Кодируем в base64-url и убираем символы "="
    code_challenge = base64.urlsafe_b64encode(code_challenge).decode('utf-8').rstrip('=')
    print(code_challenge)

    url = 'https://id.vk.com/authorize'

    params = {'response_type': 'code',
              'client_id': client_id,
              'scope': 'wall',
              'state': '123456',
              'code_challenge': code_challenge,
              'code_challenge_method': 's256'}

    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(url, params=params) as response:
                print('--2--')
                status_code = response.status
                print(status_code)

                result = await response.text()
                print(result)

                result = await response.json()
                print(result)

        except Exception as Ex:
            print(f'Error Ex {Ex}')

async def get_access_token():
    url_token = f'https://oauth.vk.com/authorize?client_id={client_id}&display=page&redirect_uri=https://sidorinlab.ru&scope=wall&response_type=token&v=5.131'


    url = 'https://id.vk.com/authorize'

    params = {'response_type': 'code',
              'client_id': client_id,
              'scope': scope,
              'redirect_uri': redirect_uri,
              'state': state,
              'code_challenge': '47DEQpj8HBSa-_TImW-5JCeuQeRkm5NMpJWZG3hSuFU',
              'code_challenge_method': 's256'
              }

    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(url, params=params) as response:
                status_code = response.status
                print(status_code)

                response_text = await response.text()
                #print(response_text)

        except Exception as Ex:
            print(f"Error Ex {Ex}")
            return

    soup = BeautifulSoup(response_text, 'html.parser')
    access_tokens = soup.find_all('script')

    for access_token in access_tokens:
        print('\n+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
        print(access_token)

        if 'access_token' not in str(access_token):
            continue

        start_index = access_token.find("{")
        print(start_index)
        end_index = access_token.rfind("}") + 1
        print(end_index)
        json_string = access_token[start_index:end_index]

        print(json_string)
        input()

async def check_vk(url):
    """
        Получает все комментарии к посту на стене ВКонтакте
        url = https://dvmn.org/encyclopedia/qna/63/kak-poluchit-token-polzovatelja-dlja-vkontakte/
        Args:
            owner_id (int): ID владельца стены (отрицательное число для групп)
            post_id (int): ID поста
            access_token (str): Токен доступа VK API

        Returns:
            list: Список комментариев

        https://dev.vk.com/ru/method/wall.getComments
        https://vkhost.github.io/
        """

    url_access_token = ('https://oauth.vk.com/authorize?'
           f'client_id={client_id}&'
           'display=page&'
           'scope=wall&'
           'response_type=token&'
           'v=5.92&'
           'state=123456')
    print(url_access_token)

    comments = []
    offset = 0

    owner_id, post_id = await extract_wall_ids(url)

    url = 'https://api.vk.com/method/wall.getComments'
    # Формируем параметры запроса
    params = {
        'owner_id': owner_id,
        'post_id': post_id,
        'count': 100,
        'offset': offset,
        'access_token': access_token,
        'v': '5.131',  # Версия API
        'extended': 1,  # Получаем расширенную информацию
        'fields': 'first_name,last_name'  # Запрашиваем имена пользователей
    }

    # Делаем запрос к API
    #response = requests.get('https://api.vk.com/method/wall.getComments', params=params)
    #data = response.json()

    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(url, params=params) as response:
                status_code = response.status
                print(status_code)
                data = await response.json()

        except Exception as Ex:
            print(f'Error Ex1 {Ex}')
            return

    #print('Data', data)

    # Проверяем наличие ошибок
    if 'error' in data:
        print(f"Ошибка: {data['error']['error_msg']}")
        return

    # Получаем информацию о комментариях
    items = data['response']['items']

    # Если комментариев больше нет, прерываем цикл
    if not items:
        return

    # Обрабатываем каждый комментарий
    for item in items:
        comment = {
            'from_id': item['from_id'],
            'date': item['date'],
            'text': item['text']
        }

        # Добавляем информацию о пользователе
        for profile in data['response']['profiles']:
            if profile['id'] == item['from_id']:
                comment['author_name'] = f"{profile['first_name']} {profile['last_name']}"
                break

        if comment.get('author_name'):
            comments.append(comment)

    print(len(comments))
    return comments

async def main_vk():
    service = await get_service()
    url = 'https://vk.com/wall-11694885_373082?reply=373184'
    url = 'https://vk.com/amurr24?w=wall-72072592_6066'

    await check_vk(url)

if __name__ == '__main__':
    #asyncio.run(check_vk(''))
    #asyncio.run(get_token())
    #asyncio.run(main_vk())
    asyncio.run(get_access_token())

# async def check_vk_sel(service, link, pattern, criteria, ss_id, project):
#     print(link)
#
#     links = await pars_url(service, ss_id, project)
#     driver = await get_selenium(link)
#
#     blocks = driver.find_elements(By.CSS_SELECTOR, 'div[id*="-"][class*="repl"][data-post-id*="-"]')
#     len_b = len(blocks)
#     print(len_b)
#
#     if len_b == 0:
#         blocks = driver.find_elements(By.CSS_SELECTOR, 'div[id*="post-"][class*="bp_post clear_fix "]')
#         len_b = len(blocks)
#
#     print(len_b)
#     if len_b == 0:
#         return
#
#     for block in blocks:
#         try:
#             date = block.find_element(By.CSS_SELECTOR, 'span[class="rel_date"]').text.split(' ')
#             print(date)
#
#         except:
#             continue
#
#         if len(date) < 3:
#             continue
#
#         day = int(date[0])
#         month = await convert_date(date[1])
#
#         if len(date) == 4:
#             year = int(datetime.now().strftime('%Y'))
#         else:
#             year = int(date[2])
#
#         target_date = datetime(year, month, day)
#         formatted_date = target_date.strftime("%d.%m.%Y")
#         print(formatted_date)
#
#         if (current_date - target_date) > timedelta(days=days_ago):
#             print(f'--- Отзыв старше {days_ago} дней = {formatted_date}.')
#             continue
#
#         url_answer = block.find_element(By.CSS_SELECTOR, 'a[class="wd_lnk"]').get_attribute('href')
#         if url_answer in links:
#             print('Такой комментарий уже есть в списке')
#             continue
#
#         print("url_answer", url_answer)
#
#         author = block.find_element(By.CSS_SELECTOR, 'a[class="author author_highlighted"]').text
#         print("author", author)
#
#         feedback = block.find_element(By.CSS_SELECTOR, 'div[class="wall_reply_text"]').text
#         print("feedback", feedback)
#
#         await generate_and_white(service=service,
#                                  url_answer=url_answer,
#                                  author=author,
#                                  formatted_date=formatted_date,
#                                  ss_id=ss_id,
#                                  project=project,
#                                  feedback=feedback,
#                                  pattern=pattern,
#                                  criteria=criteria)



# async def blocks_vk_play(playwright, browser, page):
#     #playwright, browser, page = await get_playwright(link)
#
#     if not page:
#         # await browser.close()
#         # await playwright.stop()
#         return None, None, None
#
#     blocks = await page.query_selector_all('div[id*="post"][class*="reply"][data-post-id*="-"]')
#     len_b = len(blocks)
#     print(len_b)
#
#     if len_b == 0:
#         blocks = await page.query_selector_all('div[id*="-"][class*="repl"][data-post-id*="-"]')
#         len_b = len(blocks)
#         print(len_b)
#
#     if len_b == 0:
#         blocks = await page.query_selector_all('div[id*="post-"][class="bp_post clear_fix "]')
#         len_b = len(blocks)
#         print(len_b)
#
#     if len_b == 0:
#         await browser.close()
#         await playwright.stop()
#         return None, None, None
#
#     return playwright, browser, blocks