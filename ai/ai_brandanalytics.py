from pprint import pprint

import asyncio
import os
import re
import time

from datetime import datetime, timedelta

import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
from itertools import islice

from selenium.webdriver.common.by import By

from models.mdl_tables import Prompt

from utils.central_module import get_local_ip, rec_data
from utils.db_loader import read_data_from_db_filter
from utils.gs_editor import get_service, read_table_id, write_log_sheet
from utils.user_agent import get_selenium_proxy

from portals.portal_vk import blocks_vk
from portals.youtube import blocks_youtube
from portals.portal_dzen import blocks_dzen
from portals.portal_pikaby import blocks_pikabu

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

now = datetime.now()
record_date = now.strftime("%d.%m.%Y")

year_now = now.year
month_now = now.month
day_now = now.day

days_ago = 3

username = os.environ.get("LOGIN_DA")
password = os.environ.get("PASS_DA")

auth_username = os.environ.get("HOST_USERNAME")
auth_password = os.environ.get("HOST_PASSWORD")
auth = HTTPBasicAuth(auth_username, auth_password)

sheet_id = '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8'
worksheet_name = 'BA'

proxy_on = False

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

"""
Задача:
необходимо прочитать переписку чата 
----------------НАЧАЛО ЧАТА-----------------
{chat_list} 
----------------КОНЕЦ ЧАТА------------------
и определить следующее взяв за отчетную точку следующий комментарий 
---------------НАЧАЛО КОММЕНТАРИЯ-------------
{text}
---------------КОНЕЦ КОММЕНТАРИЯ--------------
1) Упоминание находится в закрытом сообществе
2) Упоминание находится на личной странице того или иного пользователя
3) Тред мертв (то есть за обсуждаемую тему давно забыли и смысла отвечать на упоминание, которое было написано в этом обсуждени, смысла нет)
4)Тред ушел (упоминание ушло далеко вверх и в группе давно обсуждается другая тема уже)
5) Упоминание не о продукт (то есть данное упоминание тинькофф банк обходит стороной, либо же он упоминается там просто вскользь, так скажем)
6) Обобщенное упоминание (автор говорит в целом о банках, а не конкретно о тинькофф. Может просто перечислять их)
7) Упоминание размещено в аккаунте технического аккаунта (бота) (это могут быть какие-то посты в сообщетсвах, которые, к примеру, каждый день закидывает бот. Там нам так же смысла реагировать нет, поскольку мало вероятно что наше вовлечение как-то заметят)

если переписка попадает хотя бы под один пункт - выдать 'False'
иначе выдай - 'True'

Перед выполнением, прочитай задание еще раз.
"""

official = ['Альфа-Банк', "Т-Банк", "Т—Ж", "Т-Инвестиции", "Работа в Т-Банке",
            "Т-Образование", "МТС Банк", "ОТП Банк", "Банк РНКБ", "Райффайзен Банк", "Банк Уралсиб", "Точка", "МКБ",
            "Хоум Банк", "Yota", "t2", "МегаФон", "билайн Россия"]

censor = ['похе', 'срать', 'бляд', 'пизд', 'хуй', 'хуев', 'уета', 'хуёв',
          'пидар', 'пидр', 'пидор', 'педер',
          'заеб', 'заёб', 'говн', 'ебан', 'ебон', "залуп", "долба",
          "отъеб", "коллектор", "пристав", "арест"]

local_ip = asyncio.run(get_local_ip())
if '176.124.192' in local_ip:
    headless = True
    proxy_on = True

else:
    print(f'local_ip: {local_ip}')
    headless = True
    proxy_on = False

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

async def analysis_dzen(service, date_create, url_answer, first_author, prompt_trend_gone, text, driver):
    try:
        blocks, UsersByID = await blocks_dzen(driver)

    except:
        try:
            driver = await get_selenium_proxy(url_answer, headless=headless, proxy=proxy_on)
            blocks, UsersByID = await blocks_dzen(driver)

        except:
            return None

    len_blocks = len(blocks)
    print(f'Len_B = {len_blocks}')

    if len_blocks == 0:
        return driver

    comments = []

    trend_alife = False
    for block in blocks:
        #url_answer = block['entityData']['id']

        date = block['entityData']['createdTs']/1000

        # Форматирование даты
        date_content = datetime.fromtimestamp(date)
        formatted_date = date_content.strftime('%d.%m.%Y')

        if (time.time() - date) <= 3 * 24 * 3600:
            print(f'--- Отзыв младше 3 дней = {formatted_date}.')
            trend_alife = True

        author = UsersByID[block['entityData']['authorSafeUid']]

        if any(bank in author for bank in official):  # если есть ответ от оф.представителя.
            print(f"Bank = {author}")
            return driver

        feedback = block['entityData']['text']
        comments.append([date, author, feedback])

    if trend_alife == False:
        print('Тренд мертв')
        return driver

    await rec_data(service, date_create, url_answer, first_author, prompt_trend_gone, comments, text, sheet_id, worksheet_name)

    return driver

async def analysis_youtube(service, date_create, url, first_author, prompt_trend_gone, text):
    comments_content = await blocks_youtube(url)

    comments = []

    trend_alife = False
    for comment in islice(comments_content, 100):
        date = comment['time_parsed']
        feedback = comment['text']

        if time.time() - date <=  days_ago * 24 * 3600:
            print(f'--- Комментарий младше {days_ago} дней.')
            trend_alife = True

        url_answer = url + ' ' + comment['cid']
        author = comment['author']

        if any(bank in author for bank in official):  # если есть ответ от оф.представителя.
            print(f"Bank = {author}")
            return

        comments.append([date, author, feedback])

    comments.reverse()

    if trend_alife == False:
        print('Тренд мертв')
        return None

    await rec_data(service, date_create, url_answer, first_author, prompt_trend_gone, comments, text, sheet_id, worksheet_name)

async def analysis_vk(service, date_create, url_answer, first_author, prompt_trend_gone, text):
    comments = await blocks_vk(url_answer)
    #print(comments)
    await asyncio.sleep(5)

    if not comments:
        return

    trend_alife = False
    for comment in comments:
        date = comment['date']
        author = comment['author_name']

        date_ts = datetime.fromtimestamp(date)

        if (now - date_ts) <= timedelta(days=days_ago):
            print('Тренд жив.')
            trend_alife = True

        if any(bank in author for bank in official):  # если есть ответ от оф.представителя.
            print(f"Bank = {author}")
            return

    if trend_alife == False:
        print('Тренд мертв')
        return None

    await rec_data(service, date_create, url_answer, first_author, prompt_trend_gone, comments, text, sheet_id, worksheet_name)

async def analysis_pikabu(service, date_create, url_answer, first_author, prompt_trend_gone, text, driver):
    blocks = await blocks_pikabu(driver, url_answer)
    if len(blocks) == 0:
        return

    comments = []

    trend_alife = False
    for block in blocks:
        date_content = block.find_element(By.CSS_SELECTOR, 'time[class="comment__datetime hint"]')
        date_full = date_content.get_attribute("datetime")
        timestamp = datetime.strptime(date_full, '%Y-%m-%dT%H:%M:%S%z')
        date = timestamp.timestamp()
        # Форматирование даты
        formatted_date = timestamp.strftime('%d.%m.%Y')
        print(time.time(), timestamp.timestamp())
        print(time.time() - timestamp.timestamp())

        if (time.time() - timestamp.timestamp()) <= 3 * 24 * 3600:
            print(f'--- Отзыв младше 3 дней = {formatted_date}.')
            trend_alife = True

        author = block.find_element(By.CSS_SELECTOR, 'span.user__nick').text

        if any(bank in author for bank in official):  # если есть ответ от оф.представителя.
            print(f"Bank = {author}")
            return

        feedback = block.find_element(By.CSS_SELECTOR, 'p.rv-comment').text
        comments.append([date, author, feedback])

    if trend_alife == False:
        print('Тренд мертв')
        return driver

    await rec_data(service, date_create, url_answer, first_author, prompt_trend_gone, comments, text, sheet_id,
                   worksheet_name)





async def check_ba(service):
    async with aiohttp.ClientSession() as session:
        cookies = await get_cookies()

        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "DNT": "1",
            "Host": "brandanalytics.ru",
            "Origin": "https://brandanalytics.ru",
            "Priority": "u=4",
            "Referer": "https://brandanalytics.ru/summary",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "TE": "trailers",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0"
        }

        # Тело запроса
        data = {
            "blocks": {
                "theme_list": {},
                "user_settings": {}
            }
        }

        url_themes = 'https://brandanalytics.ru/report/data/'
        async with session.post(url_themes, headers=headers, cookies=cookies, json=data) as response:
            print('Resp Status:', response.status)
            if response.status == 200:
                r_json = await response.json()
                #pprint(r_json)

            else:
                return response.status

        reports = [k for k, v in r_json['theme_list'].items()]
        print("reports:", reports)

        tg_links = []

        for report in reports:
            df_links = await read_table_id(service, sheet_id, worksheet_name)
            links = df_links['portal'].to_list()
            await asyncio.sleep(3)

            url_base = f'https://brandanalytics.ru/theme-data/{report}/'

            tst = int(time.time())
            tsf = int(time.time() - 5 * 24 * 3600)

            page = 1
            limit = 100

            query = f'?tst={tst}&tsf={tsf}&requested%5B%5D=feed&sort=time_create&order=desc&page={page}&limit={limit}&filter%5Bft%5D%5Bnot%5D%5B%5D=30008&filter%5Bft%5D%5Bnot%5D%5B%5D=30009&filter%5Bft%5D%5Bnot%5D%5B%5D=15&filter%5Bft%5D%5Bnot%5D%5B%5D=30059&filter%5Bft%5D%5Bnot%5D%5B%5D=30025&filter%5Bfmsgproc%5D%5Bany%5D%5B%5D=1'
            url = url_base + query
            print('\nQuery_url:', url)

            async with aiohttp.ClientSession() as session:
                cookies = await get_cookies()

                async with session.get(url, cookies=cookies) as response:
                    if response.status == 200:
                        r_json = await response.json()
                    else:
                        continue

                messages = r_json['feed']['messages']
                len_m = len(messages)
                print(f'Len_m = {len_m}')
                if len_m == 0:
                    continue

                messages_id = [k for k, v in messages.items()]
                #input(messages_id)
                #driver = await get_selenium_proxy(proxy=proxy_on)

                status, text_prompt = await read_data_from_db_filter(Prompt, project_name='ba')

                if status:
                    prompt_trend_gone = text_prompt[0].prompt
                else:
                    return status

                driver = await get_selenium_proxy(headless=headless, proxy=proxy_on)

                for idx, msg_id in enumerate(messages_id):
                    print(f'\n******************************************{idx} ({len(messages_id) - idx})*********************************************')

                    msg = messages[msg_id]

                    author = msg['author']['fullname']
                    date_create = msg['date_create']
                    url_answer = msg['url']

                    if url_answer in links:
                        continue

                    text_highlighted = msg['text_highlighted']
                    #print('text', text_highlighted)

                    # Создаем объект BeautifulSoup
                    soup = BeautifulSoup(text_highlighted, 'html.parser')
                    # Извлекаем весь текст из документа
                    text = soup.get_text()
                    #print('text', text)
                    #input('---------------')

                    print(f'================{date_create} = {url_answer} ===================')

                    if any(mt in text.lower() for mt in censor):
                        print('>>>>>>>>>>>>>>>>>> МАТ!!! <<<<<<<<<<<<<<<<<<<<')
                        print(text)
                        continue

                    # soup = await get_soup(url_answer)
                    # if not soup:
                    #     continue
                    #
                    # if "Message in a private group or channel" in soup:
                    #     print('Телеграм - закрытая группа')
                    #     continue

                    #--------------------------------------------------------------------------------------
                    if 'vk.com' in url_answer:
                        await analysis_vk(service, date_create, url_answer, author, prompt_trend_gone, text)

                    elif 'youtube' in url_answer:
                        await analysis_youtube(service, date_create, url_answer, author, prompt_trend_gone, text)

                    elif 'pikabu' in url_answer:
                        await analysis_pikabu(service, date_create, url_answer, author, prompt_trend_gone, text, driver)






                    elif 'dzen' in url_answer:
                        driver.get(url_answer)
                        driver = await analysis_dzen(service, date_create, url_answer, author, prompt_trend_gone, text, driver)

                        if not driver:
                            driver = await get_selenium_proxy(headless=headless, proxy=proxy_on)

                    elif 'telegram' in url_answer:
                        if all(let not in url_answer for let in ['?', '/c/']):
                            tg_links.append([date_create, url_answer])
                            print(f'Add t.com: {len(tg_links)}')

                try:
                    driver.quit()
                except:
                    pass

    from portals.portal_tg import analyst_tg
    await analyst_tg(service, tg_links, prompt_trend_gone)

    return 'OK!'

async def main_ba():
    project = 'BA'
    service = await get_service()

    status = await check_ba(service)

    data = {
        'service_name': project,
            'date': time.ctime(),
            'error': status
    }
    await write_log_sheet(service, '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8', 'logs', data)

async def tst_main():
    url_answer = 'https://vk.com/wall-38889866_286572?reply=286575&thread=286573'
    text = 'Наталья, здравствуйте. А не подскажите как оформить карту Тинькофф'
    await analysis_vk('service', 'date_create', url_answer, 'author', text)

if "__main__" in __name__:
     asyncio.run(main_ba())
     #asyncio.run(tst_main())












# async def check_ba_play(service):
#     df_links = await read_table_id(service, sheet_id, worksheet_name)
#     links = df_links['portal'].to_list()
#
#     url_base = 'https://brandanalytics.ru/theme-data/12551940/'
#
#     tst = int(time.time())
#     print(datetime.utcfromtimestamp(tst).strftime('%Y-%m-%d %H:%M:%S'))
#
#     tsf = int(time.time() - 5 * 24 * 3600)
#     print(datetime.utcfromtimestamp(tsf).strftime('%Y-%m-%d %H:%M:%S'))
#
#     page = 1
#     limit = 100
#
#     query = f'?tst={tst}&tsf={tsf}&requested%5B%5D=feed&sort=time_create&order=desc&page={page}&limit={limit}&filter%5Bft%5D%5Bnot%5D%5B%5D=30008&filter%5Bft%5D%5Bnot%5D%5B%5D=30009&filter%5Bft%5D%5Bnot%5D%5B%5D=15&filter%5Bft%5D%5Bnot%5D%5B%5D=30059&filter%5Bft%5D%5Bnot%5D%5B%5D=30025&filter%5Bfmsgproc%5D%5Bany%5D%5B%5D=1'
#     url = url_base + query
#     print(url)
#
#     async with aiohttp.ClientSession() as session:
#         cookies = await get_cookies()
#         async with session.get(url, cookies=cookies) as response:
#             if response.status == 200:
#                 r_json = await response.json()
#             else:
#                 raise Exception(f"Request failed with status code {response.status}")
#
#     messages = r_json['feed']['messages']
#     #print(messages)
#     print(len(messages))
#
#     messages_id = [k for k, v in messages.items()]
#     #input(messages_id)
#
#     for idx, msg_id in enumerate(messages_id):
#         print(f'\n******************************************{idx} ({len(messages_id) - idx})*********************************************')
#
#         msg = messages[msg_id]
#
#         author = msg['author']['fullname']
#         date_create = msg['date_create']
#         url_answer = msg['url']
#
#         if url_answer in links:
#             continue
#
#         text_highlighted = msg['text_highlighted']
#         print('text', text_highlighted)
#
#         # Создаем объект BeautifulSoup
#         soup = BeautifulSoup(text_highlighted, 'html.parser')
#         # Извлекаем весь текст из документа
#         text = soup.get_text()
#         text_pars = text
#         print('text', text)
#         #input('---------------')
#
#         print(f'==================== {url_answer} ===================')
#
#         if any(mt in text.lower() for mt in ['похе', 'срать', 'бляд', 'пизд', 'хуй', 'хуев', 'уета', 'хуёв', 'пидар',
#                                              'пидр', 'пидор','заеб', 'заёб', 'говн', 'ебан', 'ебон', "залуп", "долба",
#                                              "отъеб", "коллектор", "пристав", "арест"]):
#             print('>>>>>>>>>>>>>>>>>> МАТ!!! <<<<<<<<<<<<<<<<<<<<')
#             print(text)
#             continue
#
#         soup = await get_soup(url_answer)
#         if not soup:
#             continue
#
#         if "Message in a private group or channel" in soup:
#             print('Телеграм - закрытая группа')
#             continue
#
#         if 'telegram.me' in url_answer:
#             pass
#
#         elif 'vk.com' in url_answer:
#             print(date_create)
#             print(url_answer)
#             print(text)
#
#             topic = await extract_reply(url_answer)
#             print("topic", topic)
#
#             if not topic:
#                 topic = ''
#
#             playwright, browser, page = await get_playwright(url_answer)
#             playwright, browser, blocks = await blocks_vk(playwright, browser, page)
#
#             if not blocks:
#                 if browser:
#                     await browser.close()
#                     await playwright.stop()
#                 print('Next >>>>')
#                 continue
#
#             await browser.close()
#             await playwright.stop()
#
#             chat_list = []
#
#             trend_alife = False
#             break_mode = False
#
#             for idx, block in enumerate(blocks):
#                 print(f'****************Block*{idx}*****************')
#                 try:
#                     date_content = await block.query_selector('span[class="rel_date"]')
#                     if not date_content:
#                         date_content = await block.query_selector('span[class="rel_date rel_date_needs_update"]')
#
#                     date = await date_content.inner_text()
#                     print("date =", date)
#                     date_split = date.split(' ')
#                     #print(date_split)
#
#                 except:
#                     #await browser.close()
#                     #await playwright.stop()
#                     continue
#
#                 if any(date_str in date for date_str in ['hours, today, yesterday']):
#                     trend_alife = True
#                     day = now.day
#                     month = now.month
#                     year = now.year
#
#                 elif len(date_split) == 5:
#                     day = int(date_split[0])
#                     month = await convert_date(date_split[1])
#                     year = now.year
#
#                 else:
#                     day = now.day
#                     month = now.month
#                     year = now.year
#
#                 #print(year, month, day)
#                 target_date = datetime(year, month, day)
#                 if (now - target_date) <= timedelta(days=days_ago):
#                     trend_alife = True
#
#                 id_content = await block.get_attribute('id')
#
#                 author_content = await block.query_selector('a[class="author author_highlighted"]')
#                 try:
#                     author = await author_content.inner_text()
#                 except:
#                     author = ''
#                 #print(author)
#
#                 if  any(bank in author for bank in ['Альфа-Банк', "Т-Банк"]): #если есть ответ от оф.представителя.
#                     print(f"Bank = {author}")
#                     break_mode = True
#                     break  # Выход из внутреннего цикла
#
#                 feedback_content = await block.query_selector('div[class="wall_reply_text onclick="]')
#                 try:
#                     feedback = await feedback_content.inner_text()
#                     #print(feedback)
#                 except:
#                     feedback = ''
#
#                 datas = {'date': date,
#                          'id': id_content,
#                          'author': author,
#                          'feedback': feedback}
#                 chat_list.append(datas)
#
#
#             if break_mode:
#                 continue  # Переход к следующей итерации внешнего цикла
#
#             if trend_alife == False:
#                 print('Тренд мертв!')
#                 continue
#
#             print("chat_list", chat_list)
#             user_id = [chat['id'] for chat in chat_list if topic in chat['id']]
#             if user_id:
#                 user_id = user_id[0]
#
#             else:
#                 continue
#
#             #print(user_id)
#             #print(chat_list)
#
#             prompt = prompt_vk_trend_gone.format(chat_list=chat_list, user_id=user_id)
#             #print(prompt)
#             result = await get_answer_ai(auth, prompt)
#             #print("result:", result)
#
#             if result == 'True':
#                 data = {
#                     'date_create': date_create,
#                     'portal': url_answer,
#                     'author': author,
#                     'feedback': text_pars}
#
#                 await append_data_to_sheet_scope(service, sheet_id, worksheet_name, data)
#                 print('Wrote data...')
#
# async def analysis_vk_old(service, driver, date_create, url_answer, first_author, text):
#     print(date_create)
#     print(url_answer)
#     #print(text)
#     driver.get(url_answer)
#     await asyncio.sleep(5)
#
#     text_pars = text
#
#     topic = await extract_reply(url_answer)
#     print("topic", topic)
#
#     if not topic:
#         topic = ''
#
#     #playwright, browser, page = await get_playwright(url_answer)
#
#     blocks = driver.find_elements('div[id][class]')
#
#     if not blocks:
#         # Сохранение в файл
#         page_source = driver.page_source
#         with open(f"/home/andy/PycharmProjects/sidorin/{int(time.time())}_page_source.html", "w", encoding="utf-8") as file:
#             file.write(page_source)
#
#     if not blocks:
#         if driver:
#             driver.quit()
#         print('Next >>>>')
#         return
#
#     len_b = len(blocks)
#     print(f'Len_blocks = {len_b}')
#
#     chat_list = []
#
#     trend_alife = False
#     break_mode = False
#
#     for idx, block in enumerate(blocks):
#         print(f'\n****************Block*{idx}*****************')
#         try:
#             try:
#                 print('>1 Date')
#                 date_content = block.find_element(By.CSS_SELECTOR, 'span[class="rel_date"]')
#                 print('<1 Date')
#
#             except:
#                 print('>2 Date')
#                 date_content = block.find_element(By.CSS_SELECTOR, 'span[class="rel_date rel_date_needs_update"]')
#                 print('<2 Date')
#
#             print('>3 Date')
#             date = int(date_content.get_attribute("time"))
#             print(f'<3 Date {date}')
#             date = datetime.utcfromtimestamp(date)
#             print(f'<3 Date {date}')
#
#         except Exception as Ex:
#             #print(f'Error Ex1 {Ex}')
#             try:
#                 print('>31 поиск даты')
#                 date_content = block.find_element(By.CSS_SELECTOR, 'a[class="item_date"]').text
#                 print(date_content)
#                 date_spl = date_content.split(' ')
#                 if any(day_c in date_content for day_c in ['сегодня', 'today']):
#                     date_spl_2 = date_spl[-1].split(':')
#                     print(year_now, month_now, day_now, int(date_spl_2[0], int(date_spl_2[1])))
#                     date = datetime(year_now, month_now, day_now, int(date_spl_2[0], int(date_spl_2[1])))
#                     print(date)
#
#                 elif len(date_spl) == 3:
#                     year = int(date_spl[-1])
#                     if year != year_now:
#                         print(f"{year} != {year_now}")
#                         continue
#
#                     month = months[date_spl[1]]
#                     if month != month_now:
#                         print(f"{month} != {month_now}")
#                         continue
#
#                     date = datetime(year, month, int(date_spl[0]))
#                     print(date)
#                     print('< 31')
#
#                 elif len(date_spl) == 4:
#                     if 'в' in date_spl:
#                         month = months[date_spl[1]]
#                         if month != month_now:
#                             print(f"{month} != {month_now}")
#                             continue
#
#                         date = datetime(year_now, month, int(date_spl[0]))
#                         print('< 32')
#
#             except:
#                 print('Error ? ---------------------------------------------------')
#                 #print(block.get_attribute('outerHTML'))
#                 #input('Wait... ---------------------------------------------------')
#                 continue
#
#         except:
#             print('Error ??????')
#             # print(block.get_attribute('outerHTML'))
#             # input('Wait...')
#             continue
#
#         print('++++++++++++++++')
#         print(now)
#         print(date)
#         print('++++++++++++++++')
#
#         #input('Wait...')
#
#         if (now - date) <= timedelta(days=days_ago):
#             print('Тренд жив.')
#             trend_alife = True
#
#         id_content = block.get_attribute('id')
#
#         #author_content = await block.query_selector('a[class="author author_highlighted"]')
#         try:
#             print('>4')
#             author_content = block.find_element(By.CSS_SELECTOR, 'a[class="author author_highlighted"]')
#             author = author_content.text
#             print('<4')
#
#         except:
#             try:
#                 print('>4')
#                 author_content = block.find_element(By.CSS_SELECTOR, 'a.ReplyItem__name ReplyItem__name--primaryColored')
#                 author = author_content.text
#                 # print(block.get_attribute('outerHTML'))
#                 # author_content = ''
#                 print('<4')
#
#             except:
#                 print('>5')
#                 try:
#                     author_content = block.find_element(By.CSS_SELECTOR, 'div[role="img"][alt]')
#                     author = author_content.get_attribute('alt')
#
#                 except:
#                     print('Error Name')
#                     author = ''
#                     #print(block.get_attribute('outerHTML'))
#                     #input('Next..')
#                     continue
#
#         print(author)
#
#         if any(bank in author for bank in ['Альфа-Банк', "Т-Банк"]):  # если есть ответ от оф.представителя.
#             print(f"Bank = {author}")
#             break_mode = True
#             break  # Выход из внутреннего цикла
#
#         #feedback_content = await block.query_selector('div[class="wall_reply_text onclick="]')
#         try:
#             print('>7')
#             feedback_content = block.find_element(By.CSS_SELECTOR, 'div[class="wall_reply_text onclick="]')
#             print('<7')
#         except:
#             print('>8')
#             feedback_content = block.find_element(By.CSS_SELECTOR, 'div[class="ReplyItem__body"]')
#             print('<8')
#
#         try:
#             print('>9')
#             feedback = feedback_content.text
#             # print(feedback)
#             print('<9')
#
#         except Exception as Ex:
#             print('>10')
#             print(f'Error Ex2: {Ex}')
#             feedback = ''
#             print('<10')
#
#         datas = {'date': date,
#                  'id': id_content,
#                  'author': author,
#                  'feedback': feedback}
#         chat_list.append(datas)
#
#         print('+++ Datas append!')
#
#         #print(datas)
#         #print(block.get_attribute('outerHTML'))
#         #input('Wait.1..')
#
#     if break_mode:
#         return  # Переход к следующей итерации внешнего цикла
#
#     if trend_alife == False:
#         print('Тренд мертв!')
#         return
#
#     # #print("chat_list", chat_list) #
#     # user_id = [chat['id'] for chat in chat_list if topic in chat['id']]
#     #
#     # if user_id:
#     #     user_id = user_id[0]
#     #
#     # else:
#     #     return
#     #
#     # print("user_id", user_id)
#     # # print(chat_list)
#     if len(chat_list) == 0:
#         return
#
#     df = pd.DataFrame(chat_list)
#     # Удаляем дубликаты по 'date' и сортируем
#     df = df.drop_duplicates(subset='date').sort_values(by='date').reset_index(drop=True)
#     # Преобразуем обратно в список, если это необходимо
#     chat_list = df.to_dict(orient='records')
#
#     prompt = prompt_vk_trend_gone.format(chat_list=chat_list, first_author=first_author)
#     #print(prompt)
#     result = await get_answer_ai(auth, prompt)
#     print("result:", result)
#
#     if result == 'True':
#         data = {
#             'date_create': date_create,
#             'portal': url_answer,
#             'author': first_author,
#             'feedback': text_pars}
#
#         await append_data_to_sheet_scope(service, sheet_id, worksheet_name, data)
#         print('Wrote data...')
#
#     return driver

#
# prompt_vk_trend_gone_old = """
# # Ты аналитик
# # Твоя задача:
# # прочитать переписку в виде списка
# # --------- START CHATTING ----------
# # {chat_list}
# # --------- END CHATTING -----------
# # за стартовую точку мы берем сообщение id = {user_id}
# #
# # Тебе нужно определить следующее:
# # - наше сообщение затерялось, например если от нужного нам упоминания есть ещё 10+ комментариев не относящиеся к нашему сообщению
# # - если после нашего упоминания органика перевела тему разговора и перестали говорить о нужном нам продукте/бренде/компании
# # - в сообщения пошли упоминание не о продукт (то есть данное упоминание тинькофф банк обходит стороной, либо же он упоминается там просто вскользь)
# # - обобщенное упоминание (автор говорит в целом о банках, а не конкретно о тинькофф. Может просто перечислять их)
# # и определить следующие показатели
# #
# # результат ты должен выдать в виде:
# # True - если тренд еще жив и
# # False - если тренд 'умер'.
# # """
#
# prompt_vk_trend_gone = """
# Ты аналитик
# Определите, активна или 'мертва' тенденция общения на основе списка сообщений чата.
# --------- START CHATTING ----------
# {chat_list}
# --------- END CHATTING -----------
# Получив список переписки и текст интересующего автора комментария - {text}
# для начала,
# проанализируйте сообщения, чтобы выявить следующие сценарии:
# * Сообщения, которые не связаны с исходным сообщением и упоминают продукт/бренд/компанию, отличную от интересующей вас (например, «Тинькофф Банк»).
# * Сообщения, которые меняют тему разговора и больше не обсуждают продукт/бренд/компанию после первоначального упоминания.
# * Обобщенные упоминания продуктов/брендов/компаний, в которых автор не упоминает конкретно интересующий его продукт/бренд/компанию.
#
# * Укажите, является ли тенденция все еще активной (True) или мертвой (False), исходя из этих сценариев.
# * Если ты указываешь False, напиши поясление твоего решения.
# Верни 'True' или 'False' + пояснение, в зависимости от результата.
# Перед выполнением, прочитай задание еще раз.
# """
