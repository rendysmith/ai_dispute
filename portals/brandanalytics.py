import asyncio
import os
import re
import time
import traceback
from datetime import datetime, timedelta

import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

from selenium.webdriver.common.by import By
from sqlalchemy import Executable

from portals.portal_vk import blocks_vk, convert_date
from utils.ai_module import get_answer_ai
from utils.gs_editor import get_service, append_data_to_sheet_scope, read_table_id, write_log_sheet
from utils.user_agent import get_soup, get_playwright, get_selenium_proxy

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

now = datetime.now()
now_utc = time.time()

days_ago = 3

username = os.environ.get("LOGIN_DA")
password = os.environ.get("PASS_DA")

auth_username = os.environ.get("HOST_USERNAME")
auth_password = os.environ.get("HOST_PASSWORD")
auth = HTTPBasicAuth(auth_username, auth_password)

sheet_id = '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8'
worksheet_name = 'BA'

"""
Данное упоминание нам не подходит:
1) Упоминание находится в закрытом сообществе
2) Упоминание находится на личной странице того или иного пользователя

v+t+ 3) Не допускать мат в тексте

v+ 4) Тред мертв (то есть за обсуждаемую тему давно забыли и смысла отвечать на упоминание, которое было написано в этом обсуждение, смысла нет) - #если прошло 3 дня от последнего сообщения
5) Тред ушел (упоминание ушло далеко вверх и в группе давно обсуждается другая тема уже)
Тред мёртв:
   - если от нужного нам упоминания есть ещё 10+ комментариев (уже есть полотно других сообщений и мы понимаем что заходить туда не нативно)
v+ - если упоминанию в чате уже более 2-3 дней
   - если после нашего упоминания органика перевела тему разговора и перестали говорить о нужном нам продукте/бренде/компании

7) Упоминание не о продукт (то есть данное упоминание тинькофф банк обходит стороной, либо же он упоминается там просто вскользь, так скажем)
8) Обобщенное упоминание (автор говорит в целом о банках, а не конкретно о тинькофф. Может просто перечислять их)

9) Упоминание размещено в аккаунте технического аккаунта (бота) (это могут быть какие-то посты в сообществах, которые, к примеру, каждый день закидывает бот. 
"""

prompt_vk_trend_gone_old = """
Ты аналитик 
Твоя задача:
прочитать переписку в виде списка
--------- START CHATTING ----------
{chat_list}
--------- END CHATTING -----------
за стартовую точку мы берем сообщение id = {user_id}

Тебе нужно определить следующее:
- наше сообщение затерялось, например если от нужного нам упоминания есть ещё 10+ комментариев не относящиеся к нашему сообщению
- если после нашего упоминания органика перевела тему разговора и перестали говорить о нужном нам продукте/бренде/компании
- в сообщения пошли упоминание не о продукт (то есть данное упоминание тинькофф банк обходит стороной, либо же он упоминается там просто вскользь)
- обобщенное упоминание (автор говорит в целом о банках, а не конкретно о тинькофф. Может просто перечислять их)
и определить следующие показатели

результат ты должен выдать в виде: 
True - если тренд еще жив и 
False - если тренд 'умер'.
"""

prompt_vk_trend_gone = """
Ты аналитик 
Определите, активна или 'мертва' тенденция общения на основе списка сообщений чата.
--------- START CHATTING ----------
{chat_list}
--------- END CHATTING -----------
Получив список переписки и определенный идентификатор сообщения id = {user_id} для начала, 
проанализируйте сообщения, чтобы выявить следующие сценарии: 
* Сообщения, которые не связаны с исходным сообщением и упоминают продукт/бренд/компанию, отличную от интересующей вас (например, «Тинькофф Банк»). 
* Сообщения, которые меняют тему разговора и больше не обсуждают продукт/бренд/компанию после первоначального упоминания. 
* Обобщенные упоминания продуктов/брендов/компаний, в которых автор не упоминает конкретно интересующий его продукт/бренд/компанию. 
Укажите, является ли тенденция все еще активной (True) или мертвой (False), исходя из этих сценариев. 
Верни только 'True' или 'False' в зависимости от результата.
Перед выполнением, прочитай задание еще раз.
"""


async def extract_reply(url):
    # Регулярное выражение для извлечения значения reply
    pattern = r'\?reply=(\d+)(?:&thread=\d+)?'

    # Поиск значения по шаблону
    match = re.search(pattern, url)

    if match:
        return match.group(1)
    else:
        return None

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

async def check_ba_play(service):
    df_links = await read_table_id(service, sheet_id, worksheet_name)
    links = df_links['portal'].to_list()

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

    for idx, msg_id in enumerate(messages_id):
        print(f'\n******************************************{idx} ({len(messages_id) - idx})*********************************************')

        msg = messages[msg_id]

        author = msg['author']['fullname']
        date_create = msg['date_create']
        url_answer = msg['url']

        if url_answer in links:
            continue

        text_highlighted = msg['text_highlighted']
        print('text', text_highlighted)

        # Создаем объект BeautifulSoup
        soup = BeautifulSoup(text_highlighted, 'html.parser')
        # Извлекаем весь текст из документа
        text = soup.get_text()
        text_pars = text
        print('text', text)
        #input('---------------')

        print(f'==================== {url_answer} ===================')

        if any(mt in text.lower() for mt in ['похе', 'срать', 'бляд', 'пизд', 'хуй', 'хуев', 'уета', 'хуёв', 'пидар',
                                             'пидр', 'пидор','заеб', 'заёб', 'говн', 'ебан', 'ебон', "залуп", "долба",
                                             "отъеб", "коллектор", "пристав", "арест"]):
            print('>>>>>>>>>>>>>>>>>> МАТ!!! <<<<<<<<<<<<<<<<<<<<')
            print(text)
            continue

        soup = await get_soup(url_answer)
        if not soup:
            continue

        if "Message in a private group or channel" in soup:
            print('Телеграм - закрытая группа')
            continue

        if 'telegram.me' in url_answer:
            pass

        elif 'vk.com' in url_answer:
            print(date_create)
            print(url_answer)
            print(text)

            topic = await extract_reply(url_answer)
            print("topic", topic)

            if not topic:
                topic = ''

            playwright, browser, page = await get_playwright(url_answer)
            playwright, browser, blocks = await blocks_vk(playwright, browser, page)

            if not blocks:
                if browser:
                    await browser.close()
                    await playwright.stop()
                print('Next >>>>')
                continue

            await browser.close()
            await playwright.stop()

            chat_list = []

            trend_alife = False
            break_mode = False

            for idx, block in enumerate(blocks):
                print(f'****************Block*{idx}*****************')
                try:
                    date_content = await block.query_selector('span[class="rel_date"]')
                    if not date_content:
                        date_content = await block.query_selector('span[class="rel_date rel_date_needs_update"]')
                    date = await date_content.inner_text()
                    print("date =", date)
                    date_split = date.split(' ')
                    #print(date_split)

                except:
                    #await browser.close()
                    #await playwright.stop()
                    continue

                if any(date_str in date for date_str in ['hours, today, yesterday']):
                    trend_alife = True
                    day = now.day
                    month = now.month
                    year = now.year

                elif len(date_split) == 5:
                    day = int(date_split[0])
                    month = await convert_date(date_split[1])
                    year = now.year

                else:
                    day = now.day
                    month = now.month
                    year = now.year

                #print(year, month, day)
                target_date = datetime(year, month, day)
                if (now - target_date) <= timedelta(days=days_ago):
                    trend_alife = True

                id_content = await block.get_attribute('id')

                author_content = await block.query_selector('a[class="author author_highlighted"]')
                try:
                    author = await author_content.inner_text()
                except:
                    author = ''
                #print(author)

                if  any(bank in author for bank in ['Альфа-Банк', "Т-Банк"]): #если есть ответ от оф.представителя.
                    print(f"Bank = {author}")
                    break_mode = True
                    break  # Выход из внутреннего цикла

                feedback_content = await block.query_selector('div[class="wall_reply_text onclick="]')
                try:
                    feedback = await feedback_content.inner_text()
                    #print(feedback)
                except:
                    feedback = ''

                datas = {'date': date,
                         'id': id_content,
                         'author': author,
                         'feedback': feedback}
                chat_list.append(datas)


            if break_mode:
                continue  # Переход к следующей итерации внешнего цикла

            if trend_alife == False:
                print('Тренд мертв!')
                continue

            print("chat_list", chat_list)
            user_id = [chat['id'] for chat in chat_list if topic in chat['id']]
            if user_id:
                user_id = user_id[0]

            else:
                continue

            #print(user_id)
            #print(chat_list)

            prompt = prompt_vk_trend_gone.format(chat_list=chat_list, user_id=user_id)
            #print(prompt)
            result = await get_answer_ai(auth, prompt)
            #print("result:", result)

            if result == 'True':
                data = {
                    'date_create': date_create,
                    'portal': url_answer,
                    'author': author,
                    'feedback': text_pars}

                await append_data_to_sheet_scope(service, sheet_id, worksheet_name, data)
                print('Wrote data...')

async def analysis_vk(service, date_create, url_answer, text):
    print(date_create)
    print(url_answer)
    print(text)

    text_pars = text

    topic = await extract_reply(url_answer)
    print("topic", topic)

    if not topic:
        topic = ''

    #playwright, browser, page = await get_playwright(url_answer)
    driver = await get_selenium_proxy(url_answer, proxy=False)
    await asyncio.sleep(5)
    driver, blocks = await blocks_vk(driver)

    if not blocks:
        if driver:
            driver.quit()
        print('Next >>>>')
        return

    len_b = len(blocks)
    print(f'Len_blocks = {len_b}')

    driver.quit()

    chat_list = []

    trend_alife = False
    break_mode = False

    for idx, block in enumerate(blocks):
        print(f'****************Block*{idx}*****************')
        try:
            try:
                date_content = block.find_element(By.CSS_SELECTOR, 'span[class="rel_date"]')
            except:
                date_content = block.find_element(By.CSS_SELECTOR, 'span[class="rel_date rel_date_needs_update"]')

            date = int(date_content.get_attribute("time"))

        except Exception as Ex:
            print(block.get_attribute('outerHTML'))
            input('Wait...')
            continue

        except:
            continue

        input(date)
        if (now_utc - date) <= timedelta(days=days_ago):
            trend_alife = True

        id_content = block.get_attribute('id')

        #author_content = await block.query_selector('a[class="author author_highlighted"]')
        author_content = block.find_element(By.CSS_SELECTOR, 'a[class="author author_highlighted"]')

        try:
            author = author_content.text
        except:
            author = ''
        # print(author)

        if any(bank in author for bank in ['Альфа-Банк', "Т-Банк"]):  # если есть ответ от оф.представителя.
            print(f"Bank = {author}")
            break_mode = True
            break  # Выход из внутреннего цикла

        #feedback_content = await block.query_selector('div[class="wall_reply_text onclick="]')
        feedback_content = block.find_element(By.CSS_SELECTOR, 'div[class="wall_reply_text onclick="]')
        try:
            feedback = await feedback_content.text
            # print(feedback)
        except Exception as Ex:
            print(f'Error Ex2: {Ex}')
            feedback = ''

        datas = {'date': date,
                 'id': id_content,
                 'author': author,
                 'feedback': feedback}
        chat_list.append(datas)

    if break_mode:
        return  # Переход к следующей итерации внешнего цикла

    if trend_alife == False:
        print('Тренд мертв!')
        return

    print("chat_list", chat_list)
    user_id = [chat['id'] for chat in chat_list if topic in chat['id']]
    if user_id:
        user_id = user_id[0]

    else:
        return

    # print(user_id)
    # print(chat_list)

    prompt = prompt_vk_trend_gone.format(chat_list=chat_list, user_id=user_id)
    # print(prompt)
    result = await get_answer_ai(auth, prompt)
    # print("result:", result)

    if result == 'True':
        data = {
            'date_create': date_create,
            'portal': url_answer,
            'author': author,
            'feedback': text_pars}

        await append_data_to_sheet_scope(service, sheet_id, worksheet_name, data)
        print('Wrote data...')


async def check_ba(service):
    df_links = await read_table_id(service, sheet_id, worksheet_name)
    links = df_links['portal'].to_list()

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

    for idx, msg_id in enumerate(messages_id):
        print(f'\n******************************************{idx} ({len(messages_id) - idx})*********************************************')

        msg = messages[msg_id]

        author = msg['author']['fullname']
        date_create = msg['date_create']
        url_answer = msg['url']

        if url_answer in links:
            continue

        text_highlighted = msg['text_highlighted']
        print('text', text_highlighted)

        # Создаем объект BeautifulSoup
        soup = BeautifulSoup(text_highlighted, 'html.parser')
        # Извлекаем весь текст из документа
        text = soup.get_text()
        text_pars = text
        print('text', text)
        #input('---------------')

        print(f'==================== {url_answer} ===================')

        if any(mt in text.lower() for mt in ['похе', 'срать', 'бляд', 'пизд', 'хуй', 'хуев', 'уета', 'хуёв', 'пидар',
                                             'пидр', 'пидор','заеб', 'заёб', 'говн', 'ебан', 'ебон', "залуп", "долба",
                                             "отъеб", "коллектор", "пристав", "арест"]):
            print('>>>>>>>>>>>>>>>>>> МАТ!!! <<<<<<<<<<<<<<<<<<<<')
            print(text)
            continue

        soup = await get_soup(url_answer)
        if not soup:
            continue

        if "Message in a private group or channel" in soup:
            print('Телеграм - закрытая группа')
            continue

        if 'telegram.me' in url_answer:
            pass

        elif 'vk.com' in url_answer:
            await analysis_vk(service, date_create, url_answer, text)




async def main_ba():
    project = 'BA'
    service = await get_service()

    await check_ba(service)

    data = {'service_name': project, 'date': time.ctime()}
    await write_log_sheet(service, '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8', 'logs', data)

if "__main__" in __name__:
     asyncio.run(main_ba())
