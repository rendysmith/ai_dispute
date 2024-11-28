import asyncio
import base64
import json
import os
import random
import time
import zlib
from datetime import datetime, timedelta
from pprint import pprint

import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from utils.ai_module import generate_and_white
from utils.central_module import get_local_ip, proxy_status
from utils.compressor import compress_string
from utils.constants import TABLES_LIST
from utils.converter import extract_company_name
from utils.gs_editor import get_table_scope, append_data_to_sheet_scope, pars_url, get_service, \
    append_data_to_sheet_cell, write_log_sheet
from utils.user_agent import get_data_with_proxy, get_data_without_proxy, get_selenium_proxy

current_date = datetime.now()

record_date = current_date.strftime("%d.%m.%Y")

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)
days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

ss_id = TABLES_LIST['zoom']

seven_days_ago = current_date - timedelta(days=days_ago)
formatted_7date = seven_days_ago.strftime('%Y-%m-%d')

companies = {'strakhovaja-kompanija/sberbank-strah': '147351',
             'bank/novikombank': '5bb4f769245bc22a520a62b1'}

async def get_top_url(link):
    pattern = r'https://www\.sravni\.ru/(.*?)/otzyvy/'
    link_company = await extract_company_name(pattern, link)

    if not link_company:
        return None, None

    return f"https://www.sravni.ru/{link_company}/otzyvy/", companies.get(link_company, None)

async def check_sravni(service, link, pattern, criteria, ss_id, project):
    top_url, reviewObjectId = await get_top_url(link)

    if not reviewObjectId:
        return

    if top_url:
        datas = {'project': project,
                 'url': link,
                 'top_url': top_url}

        await append_data_to_sheet_scope(service, ss_id, 'unique_url', datas)

    else:
        return

    #https://www.sravni.ru/proxy-reviews/reviews/?filterBy=withRates&fingerPrint=-1&locationRoute=&newIds=true&orderBy=byDate&pageIndex=0&pageSize=10&rated=any&reviewObjectId=147351&reviewObjectType=insuranceCompany&specificProductId=&tag=&withVotes=true
    #https://www.sravni.ru/proxy-reviews/reviews/?filterBy=all&fingerPrint=90afd98450203b85cd796220e7680745&locationRoute=&newIds=true&orderBy=byDate&pageIndex=0&pageSize=10&rated=any&reviewObjectId=147351&reviewObjectType=insuranceCompany&specificProductId=&tag=&withVotes=true
    #https://www.sravni.ru/proxy-reviews/reviews?filterBy=all&fingerPrint=90afd98450203b85cd796220e7680745&locationRoute=&newIds=true&orderBy=byDate&pageIndex=0&pageSize=10&rated=any&reviewObjectId=5bb4f769245bc22a520a62b1&reviewObjectType=banks&specificProductId=&withVotes=true
    #https://www.sravni.ru/proxy-reviews/reviews/?filterBy=all&fingerPrint=90afd98450203b85cd796220e7680745&locationRoute=&newIds=true&orderBy=byDate&pageIndex=0&pageSize=10&rated=any&reviewObjectId=147351&reviewObjectType=insuranceCompany&specificProductId=&withVotes=true
    #https://www.sravni.ru/proxy-reviews/reviews/?filterBy=all&fingerPrint=-1&                              locationRoute=&newIds=true&orderBy=byDate&pageIndex=0&pageSize=100&rated=any&reviewObjectId=147351&reviewObjectType=&               specificProductId=&tag=&          withVotes=true

    pageSize = "100"
    url = (f'https://www.sravni.ru/proxy-reviews/reviews/?'
           f'filterBy=all&'
           f'fingerPrint=-1&'
           f'locationRoute=&'
           f'newIds=true&'
           f'orderBy=byDate&'
           f'pageIndex=0&'
           f'pageSize={pageSize}&'
           f'rated=any&'
           f'reviewObjectId={reviewObjectId}&'
           f'reviewObjectType=&'
           f'specificProductId=&'
           f'tag=&'
           f'withVotes=true')

    print('Url:', url)

    local_ip = await get_local_ip()

    if '176.124.192' in local_ip:
        print('\n>>> With proxy...')
        driver = await get_selenium_proxy(url)
        # soup = BeautifulSoup(driver.page_source, 'html.parser')
        #
        # json_text = soup.find('pre').text  # Извлекаем содержимое тега <pre>
        # r = json.loads(json_text)
        # blocks = r['items']
        #
        # r = await get_data_with_proxy(url, text_format=False)
        # if not r:
        #     print('>>> WithOut proxy...')
        #     r = await get_data_without_proxy(url, text_format=False)
        #     if not r:
        #         print('Error Sravni')
        #         return

    else:
        print('\n>>> WithOut proxy...')
        driver = await get_selenium_proxy(url, proxy=False)

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    try:
        json_text = soup.find('pre').text  # Извлекаем содержимое тега <pre>

    except AttributeError:
        print('Error AE')
        print(soup)
        return

    r = json.loads(json_text)
    blocks = r['items']
    #pprint(blocks)
    #input()
        #
        # r = await get_data_without_proxy(url, text_format=False)
        # if not r:
        #     print('>>> With proxy...')
        #     r = await get_data_with_proxy(url, text_format=False)
        #     if not r:
        #         print('Error Sravni')
        #         return

    links = await pars_url(service, ss_id, project)

    #blocks = r['items']
    len_b = len(blocks)
    print('Len_B:', len_b)

    for i in blocks:
        url_answer = f"{link}{i['id']}"
        if url_answer in links:
            continue

        if i['hasCompanyResponse'] == True: #есть ответ компании
            continue

        if i['commentsCount'] > 0:
            continue

        author = i['authorName']
        if i.get('authorLastName'):
            author = f"{author} {i['authorLastName']}"

        date_str = i['createdToMoscow']
        date_str_cleaned = date_str.split('.')[0] + '+00:00'
        dt = datetime.fromisoformat(date_str_cleaned)
        dt = dt.replace(tzinfo=None)

        if (current_date - dt) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней. = {dt}')
            continue

        # Форматирование в нужный строковый формат
        formatted_date = dt.strftime('%d.%m.%Y')
        feedback = i['text']

        await generate_and_white(service=service,
                                 url_answer=url_answer,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)

    driver.quit()

async def main_sravni():
    proxy_active = await proxy_status()
    print(f'- Proxy status: {proxy_active}')

    local_ip = await get_local_ip()
    print('- local_ip', local_ip)

    service = await get_service()
    df = await get_table_scope(service, ss_id, 'zoom')
    #print(df)
    idx_num_row = df.index[df['Проект'] == 'Кол-во строк'].tolist()[0]
    df_counts = pd.Series(df.iloc[idx_num_row].values, index=df.columns).reset_index()
    df_counts[0] = pd.to_numeric(df_counts[0], errors='coerce')
    # Удаляем строки с NaN значениями в указанной колонке
    df_counts = df_counts.dropna(subset=[0])
    df_counts = df_counts.sort_values(by=0)
    #print(df_counts)

    list_ = df_counts['index'].to_list()
    print('Список проектов', list_)
    #random.shuffle(list_)

    df_uniq = await get_table_scope(service, ss_id, 'unique_url')

    df_logs = await get_table_scope(service, ss_id, 'logs')
    print(df_logs)

    for project in list_:
        if 'Проект' in project:
            continue

        #Если дата не совпадает с сегодняшней
        host_logs = ''
        project_sravni = f'sravni_{project}'
        filtered_logs = df_logs[df_logs['service_name'] == project_sravni]
        if not filtered_logs.empty:
            idx_logs = filtered_logs.index[0]

            if proxy_active != 'Active':
                await append_data_to_sheet_cell(service, ss_id, 'logs', 'proxy_status', idx_logs + 2, f'Proxy {proxy_active}')
                break

            else:
                await append_data_to_sheet_cell(service, ss_id, 'logs', 'proxy_status', idx_logs + 2,
                                                f'Proxy {proxy_active}')

            #Пропуск по дате
            date_logs = df_logs.loc[idx_logs, 'date']

            if date_logs == record_date:
                #print()
                continue
        #
        #     #Пропуск по IP
        #     host_logs = df_logs.loc[idx_logs, 'reserve']
        #     if host_logs != local_ip:
        #         print('Skip:', host_logs, local_ip)
        #         continue
        #
        # else:
        #     print(f"No logs found for service: {project}")

        df_mini = df[project]
        #print(len(df_mini))

        df_mini_pattern = df_mini[df_mini.str.contains('Пример реакции', na=False)]
        df_mini_criteria = df_mini[df_mini.str.contains('Особые критерии', na=False)]

        # Filter rows that contain 'http://'
        df_mini = df_mini[df_mini.str.contains('http', na=False)]

        # Remove duplicates
        # Удаляем дубликаты
        df_mini = df_mini.drop_duplicates().reset_index()

        df_link_list = df_mini[project].to_list()
        irec_link = [i for i in df_link_list if 'sravni' in i]
        len_irec = len(irec_link)

        if len_irec == 0:
            print(f'{project} next...')
            continue

        print(f'+++++++++++ {project} Irec link = {len_irec} ++++++++++++++')

        random.shuffle(df_link_list)

        len_df = len(df_link_list)
        print(f'\n========================= Project = {project} = Len ({len_df})==============================')

        start_time = time.time()
        list_links = []

        record = False
        for idx, link in enumerate(df_link_list):
            left = len_df - df_link_list.index(link)

            if 'sravni.ru' in link:
                print(f'\n*******************{idx}*({left})*{project}********************\n----------------- {link} ----------------')

                record = True
                top_df = df_uniq[(df_uniq['project'] == project) & (df_uniq['url'] == link)].reset_index(drop=True)

                if not top_df.empty:
                    print('Есть общая ссылка на статью')
                    link = top_df.loc[0, 'top_url']

                if link in list_links:
                    print('Ссылка уже проверена.')
                    continue

                else:
                    list_links.append(link)

                pattern = r'https://www\.sravni\.ru/(.*?)/otzyv'
                link_company = await extract_company_name(pattern, link)
                print('link_company', link_company)

                if not link_company:
                    continue

                link = f"https://www.sravni.ru/{link_company}/otzyvy/"

                if link in list_links:
                    print('Ссылка уже проверена.')
                    continue

                else:
                    list_links.append(link)

                await check_sravni(service=service,
                                  link=link,
                                  pattern=df_mini_pattern,
                                  criteria=df_mini_criteria,
                                  ss_id=ss_id,
                                  project=project)

        if record:
            finish_sec = time.time() - start_time
            datas = {'service_name': project_sravni,
                    'count': len_irec,
                    'date': record_date,
                    'time': finish_sec}

            print('datas', datas)
            await write_log_sheet(service, ss_id, 'logs', datas)

if __name__ == '__main__':
    asyncio.run(main_sravni())
