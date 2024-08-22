import asyncio
import os
import time

import aiohttp

from dotenv import load_dotenv

from bs4 import BeautifulSoup
from pydantic.validators import datetime

from utils.user_agent import get_soup
from portals.portal_vk import blocks_vk

"""
Данное упоминание нам не подходит:
1) Упоминание находится в закрытом сообществе
2) Упоминание находится на личной странице того или иного пользователя

+ 3) Не допускать мат в тексте

4) Тред мертв (то есть за обсуждаемую тему давно забыли и смысла отвечать на упоминание, которое было написано в этом обсуждени, смысла нет)
5) Тред ушел (упоминание ушло далеко вверх и в группе давно обсуждается другая тема уже)
Тред мёртв:
- если от нужного нам упоминания есть ещё 10+ комментариев (уже есть полотно других сообщений и мы понимаем что заходить туда не нативно)
- если упоминанию в чате уже более 2-3 дней
- если после нашего упоминания органика перевела тему разговора и перестали говорить о нужном нам продукте/бренде/компании

7) Упоминание не о продукт (то есть данное упоминание тинькофф банк обходит стороной, либо же он упоминается там просто вскользь, так скажем)
8) Обобщенное упоминание (автор говорит в целом о банках, а не конкретно о тинькофф. Может просто перечислять их)

9) Упоминание размещено в аккаунте технического аккаунта (бота) (это могут быть какие-то посты в сообществах, 


которые, к примеру, каждый день закидывает бот. 
"""

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

username = os.environ.get("LOGIN_DA")
password = os.environ.get("PASS_DA")

async def get_cookies() -> dict:
    url = 'https://brandanalytics.ru/account/login_check'

    payload = {
        '_username': username,
        '_password': password,
        '_remember_me': 'on'
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload) as response:
            if response.status == 200:
                # Возвращаем куки
                cookies = session.cookie_jar.filter_cookies(url)
                return {key: cookie.value for key, cookie in cookies.items()}
            else:
                raise Exception(f"Request failed with status code {response.status}")


async def check_brandanalytics():

    url_base = 'https://brandanalytics.ru/theme-data/12551940/'

    tst = int(time.time())
    print(datetime.utcfromtimestamp(tst).strftime('%Y-%m-%d %H:%M:%S'))

    tsf = int(time.time() - 5 * 24 * 3600)
    print(datetime.utcfromtimestamp(tsf).strftime('%Y-%m-%d %H:%M:%S'))

    page = 1
    limit = 100

    query = f'?tst={tst}&tsf={tsf}&requested%5B%5D=feed&sort=time_create&order=desc&page={page}&limit={limit}&filter%5Bft%5D%5Bnot%5D%5B%5D=30008&filter%5Bft%5D%5Bnot%5D%5B%5D=30009&filter%5Bft%5D%5Bnot%5D%5B%5D=15&filter%5Bft%5D%5Bnot%5D%5B%5D=30059&filter%5Bft%5D%5Bnot%5D%5B%5D=30025&filter%5Bfmsgproc%5D%5Bany%5D%5B%5D=1'
    url = url_base + query
    print(url)

    async with aiohttp.ClientSession() as session:
        cookies = await get_cookies()
        async with session.get(url, cookies=cookies) as response:
            if response.status == 200:
                r_json = await response.json()
            else:
                raise Exception(f"Request failed with status code {response.status}")


    messages = r_json['feed']['messages']
    #print(messages)
    print(len(messages))

    messages_id = [k for k, v in messages.items()]
    #input(messages_id)

    for msg_id in messages_id:
        print('\n***************************************************************************************')
        msg = messages[msg_id]

        author = msg['author']['fullname']
        date_create = msg['date_create']
        url_answer = msg['url']
        text_highlighted = msg['text_highlighted']
        # Создаем объект BeautifulSoup
        soup = await get_soup(text_highlighted, only_pars=True)
        # Извлекаем весь текст из документа
        text = soup.get_text()

        print('=======================================')
        if any(mt in text.lower() for mt in ['бляд', 'пизд', 'хуй', 'хуев', 'хуёв', 'пидар', 'пидр', 'пидор','заеб', 'заёб', 'говн', 'ебан', 'ебон', "залуп", "долба", "отъеб"]):
            print('МАТ!!!')
            print(text)
            input('WAIT...')
            continue

        soup = await get_soup(url_answer)

        if "Message in a private group or channel" in soup:
            print('Телеграм - закрытая группа')
            input('WAIT...')
            continue

        print(date_create)
        print(url_answer)
        print(text)

        if 'vk.com' in url_answer:
            playwright, browser, blocks = await blocks_vk(url_answer)

            if not blocks:
                continue

            for block in blocks:
                date_content = await block.query_selector('span[class="rel_date"]')
                if not date_content:
                    date_content = await block.query_selector('span[class="rel_date rel_date_needs_update"]')

                date = await date_content.inner_text()
                print("date =", date)




        input()



        #print(soup)







    input('OK!')


async def main():
    await check_brandanalytics()
    #cookies = await get_cookies()
    #print(cookies)


if "__main__" in __name__:
     asyncio.run(main())
