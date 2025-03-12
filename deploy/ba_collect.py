import asyncio
import os
import time
from datetime import datetime

import aiohttp
import urllib.parse

from utils.ba_conn import get_cookies, get_ids
from utils.gs_editor import read_table_id, get_service, append_data_to_sheet_scopes
from utils.user_agent import get_soup, get_soup_bs4
from utils.bert_moduls import classify_topic

from portals.portal_ok import blocks_ok
from portals.portal_tg import check_tg_link

# Получаем текущую дату
current_date = datetime.now()

# Форматируем дату в нужный формат
formatted_date = current_date.strftime("%d.%m.%Y")

print(formatted_date)

tsf = int(time.time() - 0.5 * 1 * 3600)
tst = int(time.time())

username = os.environ.get("LOGIN_BA_DASHA")
password = os.environ.get("PASS_BA_DASHA")

url_base = 'https://brandanalytics.ru/theme-data/'

gid_set = '1vxpafRIbjJriSsh9qzK_jk0ZTMJTRAX0jEep2mvBP4g'

size_limit = 200

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

    elif any(tg_link in link for tg_link in ['telegram.me', 't.me']):
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

    df_topics = await read_table_id(service, gid_set, 'product')
    topics = df_topics['topic'].to_list()

    df_platform = await read_table_id(service, gid_set, 'platform')

    df_offrep_content = await read_table_id(service, gid_set, 'offrep')
    offreps = df_offrep_content['name'].to_list()

    df_censor_content = await read_table_id(service, gid_set, 'censor')
    censors = df_censor_content['word'].to_list()

    df_set = await read_table_id(service, gid_set, 'set')

    async with aiohttp.ClientSession() as session:
        cookies = await get_cookies(session, username, password)

        for k, row in df_set.iterrows():
            link = row['link']
            #print(link)

            link_spl = link.split('/')
            #print(link_spl)

            for v in link_spl:
                if v.isdigit():
                    id_company = v
                    break

            print('ID company:',id_company)

            gid = row['gid']
            gtab = row['gtab']

            gid = '1uAgMSukxmO0KZLZ-C5mhv7c3IsxvgyD1vxaSPg3TykU'
            gtab = 'ORM (test)'
            df = await read_table_id(service, gid, gtab)
            print(df)

            links = df['Ссылка на упоминание'].to_list()

            page = 1
            len_m = size_limit
            while size_limit == len_m:
                print(f'\nPage: {page}')
                api_url = await parse_url(link, id_company, page)

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

                except:
                    print("Error:", r_json)
                    #input('wait...')

                len_m = len(messages)
                print('len_m', len_m)

                if len_m == 0:
                    break

                datas = {'Дата': [],
                         'Направление работ': [],
                         'Продукт': [],
                         'Площадка': [],
                         'Охват': [],
                         'Ссылка на упоминание': [],
                         'Текст упоминания': []
                         }

                for k, message in messages.items():
                    text_snippet_html = message['text_snippet']
                    text_snippet_content = await get_soup_bs4(text_snippet_html, only_pars=True)
                    text_snippet = str(text_snippet_content.get_text())

                    if all(wl not in text_snippet for wl in wlist):
                        continue

                    if any(censor in text_snippet for censor in censors):
                        print(f'-- IS NOT Censor: {text_snippet}')
                        continue

                    audience = int(message['counterList']['audience']) / 1000
                    if audience <= 2:
                        print('--- Охват меньше 2000')
                        continue

                    fullname = message['author']['fullname']
                    print(fullname)

                    if any(offrep in fullname for offrep in offreps):
                        print(f'-- IS official: {fullname}')
                        continue

                    url_comment = message['url']
                    if url_comment in links:
                        continue

                    #Если это сообщество официала.
                    if 'vk.com' in url_comment:
                        group_name = await blocks_ok(url_comment)
                        if any(offrep in group_name for offrep in offreps):
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
                    index_name = (df_platform['hub_name'] == hub_name).idxmax()
                    platform = df_platform.loc[index_name, 'gs_name']
                    #print(platform)

                    product, confidence = await classify_topic(text_snippet, topics)

                    text_snippet = "'" + text_snippet

                    datas['Дата'].append(formatted_date)
                    datas['Направление работ'].append(work_area)
                    datas['Продукт'].append(product)
                    datas['Площадка'].append(platform)
                    datas['Охват'].append(audience)
                    datas['Ссылка на упоминание'].append(url_comment)
                    datas['Текст упоминания'].append(text_snippet)

                if len(datas):
                    pass
                    await append_data_to_sheet_scopes(service, gid, gtab, datas)

                page += 1
                input(f'next...page = {page}')
                await asyncio.sleep(5)






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



if "__main__" == __name__:
    asyncio.run(main())