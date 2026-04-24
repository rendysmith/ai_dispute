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

from utils.constants import months

from utils.central_module import get_local_ip, rec_data, get_hpo
from utils.db_loader import read_data_from_db_filter
from utils.gs_editor import get_service, read_table_id, write_log_sheet
from utils.user_agent import get_selenium_proxy, ua, get_soup
from utils.ba_conn import get_cookies

from portals.portal_vk import blocks_vk
from portals.youtube import blocks_youtube
from portals.portal_dzen import blocks_dzen
from portals.portal_pikaby import blocks_pikabu
from portals.portal_ok import blocks_ok

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

now = datetime.now()

record_date = now.strftime("%d.%m.%Y")

year_now = now.year
month_now = now.month
day_now = now.day

days_ago = 3

username = os.environ.get("LOGIN_BA_ANKU")
password = os.environ.get("PASS_BA_ANKU")

auth_username = os.environ.get("HOST_USERNAME")
auth_password = os.environ.get("HOST_PASSWORD")
auth = HTTPBasicAuth(auth_username, auth_password)

tsf = int(time.time() - 5 * 24 * 3600)
tst = int(time.time())

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

print('BA')

headless, proxy_on, only_text = asyncio.run(get_hpo())

# local_ip = asyncio.run(get_local_ip())
# if '176.124.192' in local_ip:
#     headless = True
#     proxy_on = True
#
# else:
#     print(f'local_ip BA: {local_ip}')
#     headless = False
#     proxy_on = False

#
# def set_locale():
#     if sys.platform.startswith("win"):  # Windows
#         try:
#             locale.setlocale(locale.LC_TIME, "Russian_Russia.1251")  # Русская локаль для Windows
#         except locale.Error:
#             locale.setlocale(locale.LC_TIME, "en_US.UTF-8")  # Запасной вариант
#     else:  # Linux / macOS
#         os.environ["LANG"] = "ru_RU.UTF-8"
#         os.environ["LC_ALL"] = "ru_RU.UTF-8"
#
#         try:
#             locale.setlocale(locale.LC_TIME, "C.UTF-8")
#         except locale.Error:
#             locale.setlocale(locale.LC_TIME, "en_US.UTF-8")  # Запасной вариант

async def extract_reply(url):
    # Регулярное выражение для извлечения значения reply
    pattern = r'\?reply=(\d+)(?:&thread=\d+)?'

    # Поиск значения по шаблону
    match = re.search(pattern, url)

    if match:
        return match.group(1)
    else:
        return None

async def analysis_dzen(service, date_create, url_answer, first_author, prompt_trend_gone, text, driver):
    #headless, proxy_on, only_text = await get_hpo()

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

        try:
            feedback = block['entityData']['text']
        except:
            feedback = ''

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

async def analysis_ok(service, date_create, url_answer, first_author, prompt_trend_gone, text):
    #set_locale()

    blocks = await blocks_ok(url_answer)
    if len(blocks) == 0:
        return

    comments = []

    trend_alife = False
    for block in blocks:
        date_str = block.find('span', {'class': 'comments_current__footer__main__date'}).text
        try:
            date_obj = datetime.strptime(date_str, "%d %b %Y")

        except:
            date_str_str = date_str.split(' ')
            if months.get(date_str_str[1]):
                number_month = months.get(date_str_str[1])

                date_str = date_str.replace(date_str_str[1], number_month)
                date_obj = datetime.strptime(date_str, "%d %m")

            else:
                print("-- date_str_str:", date_str_str)
                continue

        if (now - date_obj) <= timedelta(days=days_ago):
            print('Тренд жив.')
            trend_alife = True

        try:
            author = block.find('a', {'class': 'comments_current__header__main__author__name'}).text
        except:
            author = block.find('a', {'class': 'comments_author-name o'}).text

        if any(bank in author for bank in official):  # если есть ответ от оф.представителя.
            print(f"Bank = {author}")
            return

        feedback = block.find('span', {'class': 'js-text-full'}).text
        comments.append([date_str, author, feedback])

    if trend_alife == False:
        print('Тренд мертв')
        return None

    await rec_data(service, date_create, url_answer, first_author, prompt_trend_gone, comments, text, sheet_id,
                   worksheet_name)

async def analysis_pikabu(service, date_create, url_answer, first_author, prompt_trend_gone, text, driver):
    blocks = await blocks_pikabu(driver)
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

        if (time.time() - timestamp.timestamp()) <= 3 * 24 * 3600:
            print(f'--- Отзыв младше 3 дней = {formatted_date}.')
            trend_alife = True

        author = block.find_element(By.CSS_SELECTOR, 'span.user__nick').text

        if any(bank in author for bank in official):  # если есть ответ от оф.представителя.
            print(f"Bank = {author}")
            return

        try:
            feedback = block.find_element(By.CSS_SELECTOR, 'p.rv-comment').text
        except:
            feedback = ''

        comments.append([date, author, feedback])

    if trend_alife == False:
        print('Тренд мертв')
        return driver

    await rec_data(service, date_create, url_answer, first_author, prompt_trend_gone, comments, text, sheet_id,
                   worksheet_name)

    return driver

async def report_data(session, cookies):
    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'DNT': '1',
        'Host':	'brandanalytics.ru',
        'Origin': 'https://brandanalytics.ru',
        'Priority': 'u=4',
        'Referer': f'https://brandanalytics.ru/report/12551940/summary?tsf={tsf}&tst={tst}',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'TE': 'trailers',
        'User-Agent': ua.firefox
    }

    data = {'blocks':
        {
        "groups": {},
        "theme_list": {},
        "user_settings": {}
        }}

    url_themes = 'https://brandanalytics.ru/report/data/'
    async with session.post(url_themes, headers=headers, json=data, cookies=cookies) as response:
        print('Status:', response.status)
        if response.status == 200:
            r_json = await response.json()

        else:
            print(response)
            return response.status

    # reports = [k for k, v in r_json['user_settings']['userRoles'].items() if k.isdigit()]
    # print(reports)
    # print(len(reports))

    reports = [k for k, v in r_json['user_settings']['userPermissions'].items()]
    print(reports)
    return reports, headers

async def check_ba(service):
    async with aiohttp.ClientSession() as session:
        cookies = await get_cookies(session, username, password)

        #reports, headers = await get_ids(session, cookies)
        reports, headers = await report_data(session, cookies)
        print("reports:", reports)

        tg_links = []

        #------------------------------------------------------
        #reports = ['13746174']
        #------------------------------------------------------

        for report in reports:
            print(f"**************{report}********************")
            df_links = await read_table_id(service, sheet_id, worksheet_name)
            links = df_links['portal'].to_list()
            await asyncio.sleep(3)

            #report = '12551940'

            url_base = f'https://brandanalytics.ru/theme-data/{report}/'

            page = 1
            limit = 100

            # data = {
            #     'tst': f"{tst}",
            #     'tsf': f"{tsf}",
            #     'requested[]': "feed",
            #     'sort':	"time_create",
            #     'order': "desc",
            #     'page': "1",
            #     'size': "50",
            #     'limit': "25"
            # }
            #
            # print('---------------------------')
            # async with session.post(url_base, headers=headers, cookies=cookies, data=data) as response:
            #     if response.status == 200:
            #         r_json = await response.json()
            #         print(response.status)
            #
            #     else:
            #         print(response.status)
            #         #continue


            query = f'?tst={tst}&tsf={tsf}&requested%5B%5D=feed&sort=time_create&order=desc&page={page}&limit={limit}&filter%5Bft%5D%5Bnot%5D%5B%5D=30008&filter%5Bft%5D%5Bnot%5D%5B%5D=30009&filter%5Bft%5D%5Bnot%5D%5B%5D=15&filter%5Bft%5D%5Bnot%5D%5B%5D=30059&filter%5Bft%5D%5Bnot%5D%5B%5D=30025&filter%5Bfmsgproc%5D%5Bany%5D%5B%5D=1'
            url = url_base + query
            print('\nQuery_url:', url)

            async with aiohttp.ClientSession() as session:
                cookies = await get_cookies(session, username, password)

                async with session.get(url, cookies=cookies) as response:
                    if response.status == 200:
                        try:
                            r_json = await response.json()

                        except Exception as Ex:
                            print(f'Error Ex: {Ex}')
                            print(await response.text())
                            continue

                    else:
                        print(f'Status code: {response.status}')
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

                    elif 'youtube.com' in url_answer:
                        await analysis_youtube(service, date_create, url_answer, author, prompt_trend_gone, text)

                    elif 'ok.ru' in url_answer:
                        await analysis_ok(service, date_create, url_answer, author, prompt_trend_gone, text)

                    elif 'pikabu' in url_answer:
                        if '?' in url_answer:
                            url_answer = url_answer.split('?')[0] + '#comments'

                        print('url_answer', url_answer)
                        try:
                            driver.get(url_answer)

                        except:
                            driver = await get_selenium_proxy(headless=headless, proxy=proxy_on)
                            await asyncio.sleep(5)
                            driver.get(url_answer)

                        driver = await analysis_pikabu(service, date_create, url_answer, author, prompt_trend_gone, text, driver)
                        if not driver:
                            driver = await get_selenium_proxy(headless=headless, proxy=proxy_on)
                            await asyncio.sleep(5)

                    elif 'dzen' in url_answer:
                        try:
                            driver.get(url_answer)

                        except:
                            driver = await get_selenium_proxy(headless=headless, proxy=proxy_on)
                            await asyncio.sleep(5)
                            driver.get(url_answer)

                        driver = await analysis_dzen(service, date_create, url_answer, author, prompt_trend_gone, text, driver)

                        if not driver:
                            driver = await get_selenium_proxy(headless=headless, proxy=proxy_on)
                            await asyncio.sleep(5)

                    elif 'telegram' in url_answer:
                        if all(let not in url_answer for let in ['?', '/c/']):
                            tg_links.append([date_create, url_answer])
                            print(f'Add t.com: {len(tg_links)}')

                try:
                    driver.quit()
                except:
                    pass

    if len(tg_links) == 0:
        return 'OK!'

    from portals.portal_tg import analyst_tg
    await analyst_tg(service, tg_links, prompt_trend_gone)

    return 'OK!'

async def main_ba():
    SS_ID = '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8'
    project = 'BA'
    service = await get_service()
    status = await check_ba(service)

    data = {
        'service_name': project,
            'date': time.ctime(),
            'error': status
    }
    await write_log_sheet(service, SS_ID, 'logs', data)

async def tst_main():
    url_answer = 'https://vk.com/wall-38889866_286572?reply=286575&thread=286573'
    text = 'Наталья, здравствуйте. А не подскажите как оформить карту Тинькофф'
    await analysis_vk('service', 'date_create', url_answer, 'author', text)

if "__main__" in __name__:
     asyncio.run(main_ba())
     #asyncio.run(tst_main())
