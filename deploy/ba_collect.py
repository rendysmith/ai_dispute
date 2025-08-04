from pprint import pprint

import asyncio
import os
import time
from datetime import datetime

import aiohttp
import urllib.parse

import pandas as pd
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

from utils.ai_module import get_answer_ai
from utils.ba_conn import get_cookies, get_ids
from utils.gs_editor import read_table_id, get_service, append_data_to_sheet_scopes, read_all_worksheets, get_spreadsheet_title
from utils.user_agent import get_soup, get_soup_bs4
from utils.bert_moduls import classify_topic, anti_ads

from portals.portal_ok import blocks_ok
from portals.portal_vk import blocks_vk
from portals.portal_tg import check_tg_link


# Получаем текущую дату
current_date = datetime.now()

# Форматируем дату в нужный формат
formatted_date = current_date.strftime("%d.%m.%Y")

print("formatted_date", formatted_date)

tsf = int(time.time() - 1 * 1 * 3600) #взять пока за последний час, нужно будет за последние 3 дня.
tst = int(time.time())

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

HOST_USERNAME = os.environ.get("HOST_USERNAME")
HOST_PASSWORD = os.environ.get("HOST_PASSWORD")
auth = HTTPBasicAuth(HOST_USERNAME, HOST_PASSWORD)

username = os.environ.get("LOGIN_BA_DASHA")
password = os.environ.get("PASS_BA_DASHA")

url_base = 'https://brandanalytics.ru/theme-data/'

gid_set = '1vxpafRIbjJriSsh9qzK_jk0ZTMJTRAX0jEep2mvBP4g'

size_limit = 100

async def parse_url(url, id_company, page):
    # Разделение базовой ссылки и параметров
    base_url, params = url.split('?')
    params_dict = urllib.parse.parse_qs(params)

    params_dict['tsf'] = [tsf]
    params_dict['tst'] = [tst]

    # Составление новой ссылки для API
    api_url = f'https://brandanalytics.ru/theme-data/{id_company}/?requested%5B%5D=feed&sort=time_create&order=desc&page={str(page)}&size={str(size_limit)}&limit={str(size_limit)}&{urllib.parse.urlencode(params_dict, doseq=True)}'
    print(api_url)
    return api_url

async def check_link(link):
    if 'ok.ru' in link:
        print('--- Check link ok.ru')
        blocks = await blocks_ok(link)
        if len(blocks) == 0:
            return False
        else:
            return True

    elif any(tg_link in link.lower() for tg_link in ['telegram.me', 't.me']):
        print('--- Check link t.me!')
        status_tg = await check_tg_link(link)
        if status_tg:
            return False
        else:
            return True

    return True

# print(asyncio.run(check_link('https://telegram.me/c/2082156527/2086958')))
# print(asyncio.run(check_link('https://telegram.me/chat_easyi/3678228')))
# print(asyncio.run(check_link('https://telegram.me/chat_easyi/3678228')))
# input()


async def main():
    service = await get_service()

    df_wl = await read_table_id(service, gid_set, 'white_list')
    wlist = df_wl['word'].to_list()

    df_products = await read_table_id(service, gid_set, 'product')
    #topics = df_topics['topic'].to_list()

    df_platform = await read_table_id(service, gid_set, 'platform')

    df_offrep_content = await read_table_id(service, gid_set, 'offrep')
    offreps = df_offrep_content['name'].to_list()

    df_censor_content = await read_table_id(service, gid_set, 'censor')
    censors = df_censor_content['word'].to_list()

    df_llm = await read_table_id(service, gid_set, 'LLM')
    df_llm_prompt = df_llm[['text', 'comment']]

    df_set = await read_table_id(service, gid_set, 'set')

    #TEST ------------------------------------------------------------------------------------------
    df_set = pd.DataFrame({'link': ["https://brandanalytics.ru/report/13829032/summary?tsf=1753131600&tst=1753390799&fmsgproc[any]=1&fsource[any]=3&fsource[any]=18&fsource[any]=38475&fsource[any]=59075&fsource[any]=19&fthematic[any]=-9&fsource[not]=21&fsource[not]=14497&fsource[not]=1&fsource[not]=122919&fsource[not]=31225&fsource[not]=583&ft[not]=83&ft[not]=36&ft[not]=91&ft[not]=87&ft[not]=88&ft[not]=93&ft[not]=84&ft[not]=92&ft[not]=90&ft[not]=109&ft[not]=129&ft[not]=107&ft[not]=97&ft[not]=89&ft[not]=96&ft[not]=82&far[any]=1500&far[any]=0"],
                           "gid": ['1uAgMSukxmO0KZLZ-C5mhv7c3IsxvgyD1vxaSPg3TykU'],
                           "gtab": ['ORM (test)']})
    print(df_set)
    #-----------------------------------------------------------------------------------------------

    async with aiohttp.ClientSession() as session:
        #cookies = await get_cookies(session, username, password)

        for k, row in df_set.iterrows():

            gid = row['gid']
            worksheet_names = await get_spreadsheet_title(service, gid)

            clients_name = set(df_products['Имя клиента'].tolist())

            for client_name in clients_name:
                if client_name in worksheet_names:
                    df_products_podproducts = df_products[df_products["Имя клиента"] == client_name]
                    product_list = df_products_podproducts['Продукт'].drop_duplicates().tolist()
                    break

            print(df_products_podproducts)
            print(product_list)

            link = row['link']
            link_spl = link.split('/')
            #print(link_spl)

            for v in link_spl:
                if v.isdigit():
                    id_company = v
                    break

            print('ID company:',id_company)

            gid = row['gid']
            gtab = row['gtab']

            # gid = '1uAgMSukxmO0KZLZ-C5mhv7c3IsxvgyD1vxaSPg3TykU'
            # gtab = 'ORM (test)'
            df = await read_table_id(service, gid, gtab)
            print(df)

            links = df['Ссылка на упоминание'].to_list()

            page = 1
            len_m = size_limit
            while size_limit == len_m:
                print(f'\nPage: {page}')
                api_url = await parse_url(link, id_company, page)

                cookies = await get_cookies(session, username, password)
                async with session.get(api_url, cookies=cookies) as response:
                    if response.status == 200:
                        try:
                            r_json = await response.json()

                        except Exception as Ex:
                            print(f"Error Ex: {Ex}\n{await response.text()}")
                            continue

                    else:
                        print(f'Status: {response.status}')
                        continue

                try:
                    messages = r_json['feed']['messages']

                except Exception as Ex:
                    print(f"Error Ex2: {Ex}")
                    input('wait...')

                len_m = len(messages)
                print('len_m =', len_m)

                if len_m == 0:
                    break

                datas = {'Дата': [],
                         'Направление работ': [],
                         'Продукт': [],
                         'Подпродукт': [],
                         'Площадка': [],
                         'Охват': [],
                         'Ссылка на упоминание': [],
                         'Текст упоминания': [],
                         'Комментарий': []
                         }

                for k, message in messages.items():
                    print(f'-- Page {page}, message #{k}')
                    text_snippet_html = message['text_snippet']
                    text_snippet_content = await get_soup_bs4(text_snippet_html, only_pars=True)
                    text_snippet = str(text_snippet_content.get_text())

                    if all(wl not in text_snippet for wl in wlist):
                        continue

                    if any(censor in text_snippet.lower() for censor in censors):
                        print(f'-- IS NOT Censor: {text_snippet}')
                        continue

                    #Указать аудиторию
                    mix_audience = 1.5
                    audience = int(message['counterList']['audience']) / 1000
                    if audience <= mix_audience:
                        print(f'--- Охват меньше {mix_audience} тыс.')
                        continue

                    fullname = message['author']['fullname']
                    #print(fullname)

                    #имена официалов
                    if any(offrep in fullname.lower() for offrep in offreps):
                        print(f'-- IS official: {fullname}')
                        continue

                    url_comment = message['url']
                    if url_comment in links:
                        continue

                    #Если это сообщество официала.
                    if 'vk.com' in url_comment:
                        group_name = await blocks_vk(url_comment, author_name=True)
                        if any(offrep in group_name.lower() for offrep in offreps):
                            print(f'-- IS official group name: {group_name}')
                            continue

                    #Проверка ссылки на приватность и наличие коментов.
                    status_link = await check_link(url_comment)
                    if not status_link:
                        continue

                    tone_mark = message['tone_mark']

                    if tone_mark in [0, 1]:
                        work_area = 'Орм Позитив'

                    else:
                        work_area = 'Реагирование Без VC'

                    hub_name  = message['hub_name']
                    #print(hub_name)
                    #Определение платфоры для комента
                    index_name = (df_platform['hub_name'] == hub_name).idxmax()
                    platform = df_platform.loc[index_name, 'gs_name']
                    #print(platform)

                    #Проверка текста на косвенность.

                    text_ba = """Внимательно изучи массив данных
                    ----------------НАЧАЛО ДАННЫХ---------------
                    {df_llm_prompt}
                    ----------------КОНЕЦ ДАННЫХ----------------
                    text - Комментарий о товаре или услуге                                            
                    comment - Причина почему этот комментарий не подходит для дальнейшего анализа
                    На основании приложенного выше массива данных, ты должен проанализировать следующий текст
                    ---------------НАЧАЛО ТЕКСТА-----------------
                    {text_snippet}
                    ---------------КОНЕЦ ТЕКСТА------------------
                    Твоя задача выявить можно ли брать данный текст для дальнейшего анализа или нет.
                    Если текст можно брать для последующего анализа дай результат в виде текста "CONTINUE"
                    Если текст похож на тот что в массиве и не подходит для дальнейшего анализа выведи результат в виде текста "STOP"
                    Дополнительно можешь написать, почему ты принял такое решение.
                    """

                    prompt = text_ba.format(df_llm_prompt=df_llm_prompt, text_snippet=text_snippet)
                    result = await get_answer_ai(auth, prompt)

                    if 'STOP'.lower() in result.lower():
                        #print("--- AI analyst result:\n", result)
                        datas['Комментарий'].append(result)
                        #continue

                    else:
                        datas['Комментарий'].append('')
                        print('+++ Data')

                    print("product_list:", product_list)

                    #поиск продукта с помощью BERT
                    product, confidence = await classify_topic(text_snippet, product_list)
                    print("product:", product)

                    if product == "Неопределено":
                        podproduct = product

                    else:
                        podproduct_list = df_products_podproducts['Подпродукт'][df_products_podproducts['Продукт'] == product].drop_duplicates().tolist()
                        print("podproduct_list:", podproduct_list)

                        if len(podproduct_list) < 2:
                            podproduct = podproduct_list[0]

                        else:
                            podproduct, podconfidence = await classify_topic(text_snippet, podproduct_list)

                    text_snippet = "'" + text_snippet

                    datas['Дата'].append(formatted_date)
                    datas['Направление работ'].append(work_area)
                    datas['Продукт'].append(product)
                    datas['Подпродукт'].append(podproduct)
                    datas['Площадка'].append(platform)
                    datas['Охват'].append(audience)
                    datas['Ссылка на упоминание'].append(url_comment)
                    datas['Текст упоминания'].append(text_snippet)

                print("datas")
                print(datas)

                if len(datas['Дата']):
                    print('+++++++++++++++++++++++++++')
                    await append_data_to_sheet_scopes(service, gid, gtab, datas)
                    print('+++++++++++++++++++++++++++')

                else:
                    print('--- NO datas...')

                page += 1
                input(f'next...page = {page}')
                await asyncio.sleep(5)

                if len_m < size_limit:
                    break








        # id_themes, headers = await get_ids(session, cookies)
        # print(id_themes)
        #
        # page = 1
        # limit = 100
        # id_card = id_themes.get('(SERM/ORM) T-Bank (ВЕСЬ!) SL (Обработка)')
        # print(id_card)
        #
        # url = os.path.join(url_base, id_card, query)
        #
        # async with session.post(url, cookies=cookies) as response:
        #     if response.status == 200:
        #         try:
        #             r_json = await response.json()
        #
        #         except:
        #             print('error')
        #
        #     else:
        #         print('Status:', response.status)
        #
        # messages = r_json['feed']['messages']
        # print(len(messages))






#url = 'https://brandanalytics.ru/report/12551940/summary?tsf=1739566800&tst=1739825999&fmsgproc[any]=1&ft[not]=30008&ft[not]=30009&ft[not]=15&ft[not]=30029&ft[not]=30059&ft[not]=30025&fsource[not]=14497&fsource[not]=21&fsource[not]=583&fsource[not]=10273&fsource[not]=122919&fsource[not]=150992&fsource[not]=60312'
#url = 'https://brandanalytics.ru/theme-data/12551940/?tst=1739825999&tsf=1739566800&requested%5B%5D=feed&sort=time_create&order=desc&page=1&size=50&limit=25&filter%5Bfmsgproc%5D%5Bany%5D%5B%5D=1&filter%5Bft%5D%5Bnot%5D%5B%5D=30008&filter%5Bft%5D%5Bnot%5D%5B%5D=30009&filter%5Bft%5D%5Bnot%5D%5B%5D=15&filter%5Bft%5D%5Bnot%5D%5B%5D=30029&filter%5Bft%5D%5Bnot%5D%5B%5D=30059&filter%5Bft%5D%5Bnot%5D%5B%5D=30025&filter%5Bfsource%5D%5Bnot%5D%5B%5D=14497&filter%5Bfsource%5D%5Bnot%5D%5B%5D=21&filter%5Bfsource%5D%5Bnot%5D%5B%5D=583&filter%5Bfsource%5D%5Bnot%5D%5B%5D=10273&filter%5Bfsource%5D%5Bnot%5D%5B%5D=122919&filter%5Bfsource%5D%5Bnot%5D%5B%5D=150992&filter%5Bfsource%5D%5Bnot%5D%5B%5D=60312'

async def tst():

    texts = ['...от Т-Банка. Сим-карта уже с двумя номерами. tbank.ru/baf/9vyrRt4IP5W При переносе номера получите 2 000 рублей. Оплати связь на 500 р и они тебе вернутся подарком. В тариф входят безлимитные соцсети и...',
             'Сегодня заработал билайн, Тинькофф пока нет',
             'Т мобайл не работает',
             'Т-Банк, то есть ни вай фая,ни связи,ни заказ сделать...',
             '...от Т-Банка. Сим-карта уже с двумя номерами. tbank.ru/baf/9vyrRt4IP5W При переносе номера получите 2 000 рублей. Оплати связь на 500 р и они тебе вернутся подарком. В тариф входят безлимитные соцсети и...']

    for text in texts:
        await anti_ads(text)

    input()



    service = await get_service()
    df_censor_content = await read_table_id(service, gid_set, 'censor')
    censors = df_censor_content['word'].to_list()
    print(censors)

    text_snippet = '...перенос номера! Мошенники!!! Уже без причины откладывают перенос номера в Т мобайл!! Раньше говорили несовпадение данных, когда данные подправили уже причину не пишут, просто перенос не...'

    if any(censor in text_snippet.lower() for censor in censors):
        print(f'-- IS NOT Censor: {text_snippet}')

    else:
        print('Не пропускаем')


    # blocks = await blocks_vk("http://vk.com/wall-20225241_1026462?reply=1059663&thread=1029932", author_name=True)
    # print(blocks)
    #
    input('Wait...')





    service = await get_service()
    df_products = await read_table_id(service, gid_set, 'product')

    df_products_podproducts = df_products[df_products["Имя клиента"] == "Ингрид"]
    print(df_products)

    product_list = df_products_podproducts['Продукт'].drop_duplicates().tolist()


    podproduct_list = df_products_podproducts['Подпродукт'][df_products_podproducts['Продукт'] == 'РК "название"'].drop_duplicates().tolist()

    print(podproduct_list)
    input()


    text_snippets = ["...экскурсии в любой уголок Крыма, морские прогулки, рыбалка, поездки в горы и на водопад Джур-Джур... Бронирование номеров по предоплате 10% от общей суммы на карту Тинькофф...",
                     "Светлана, у меня Тинькофф, я за себя говорю...",
                     'У меня Тинькоф уже неделю интернет не даёт, хотя у других операторов более-менее нормально)',
                     'Оленька, Тинькофф мобаил тоже пашет...']
    product_list = ['Мобайл', 'Путешествия', 'Город', 'Выгода', 'Шоппинг', 'РК "название"']
    product, confidence = await classify_topic(text_snippet, product_list)
    print(product)
    print(confidence)

if "__main__" == __name__:
    #asyncio.run(main())
    asyncio.run(tst())