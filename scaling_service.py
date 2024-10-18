import os.path
import time
from datetime import datetime

import pandas as pd
import requests

import asyncio
import re
import random

import traceback

from dotenv import load_dotenv

from portals.portal_aplaut import check_aplout
from portals.portal_rustore import check_rustore
from portals.portal_ya_market import check_ya_market
from portals.pravda_sotrudnikov import check_pravda
from portals.dreamjob import check_dreamjob
from portals.portal_2gis import check_2gis
from portals.portal_ya import check_ya
from portals.portal_dzen import check_dzen
from portals.portal_sravni import check_sravni
from portals.ocompanii import check_ocompanii
from portals.irecommend import check_irecommend
from portals.portal_drive2 import check_drive2
from portals.portal_otzovik import check_otzovik
#from portals.portal_vk import check_vk
from portals.portal_otvet import check_otvet
from portals.youtube import check_youtube
from portals.rocketdata import check_rocketdata
from utils.converter import extract_company_name

from utils.gs_editor import get_service, get_table_scope, append_data_to_sheet_scope, write_log_sheet

from utils.constants import TABLES_LIST
from utils.user_agent import get_playwright

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

max_sec = int(os.environ.get("MAX_SEC"))

ss_id = TABLES_LIST['zoom']
current_date = datetime.now().strftime("%d.%m.%Y")

async def get_set():
    url = 'http://147.45.164.92/json/parsing.php'
    r = requests.get(url)
    status_code = r.status_code
    if status_code == 200:
        r_json = r.json()
        timetable = [k for k, v in r_json['Timetable'].items() if v == 'True']
        projects = [k for k, v in r_json['projects'].items() if v == 'True']
        portal = [k for k, v in r_json['portal'].items() if v == 'True']
        return timetable, projects, portal

    else:
        return [], [], []

async def get_local_ip():
    url = 'https://api.myip.com/'
    r = requests.get(url)
    if r.status_code == 200:
        if r.json().get('ip'):
            return r.json()['ip']

    url = 'https://api.ipify.org?format=json'
    r = requests.get(url)
    if r.status_code == 200:
        if r.json().get('ip'):
            return r.json()['ip']

    url = 'https://ifconfig.me/all.json'
    r = requests.get(url)
    if r.status_code == 200:
        if r.json().get('ip_addr'):
            return r.json()['ip_addr']

    else:
        return '127.0.0.1'

async def fix_error(service, project, portal, error):
    data = {
        'date': time.ctime(),
        'project': project,
        'portal': portal,
        'error': error,
    }

    tab_name = 'ERRORS'
    await append_data_to_sheet_scope(service, ss_id, tab_name, data)

async def time_out_on(async_func, timeout=180, **kwargs):
    ts = random.randint(5, max_sec)
    print(f'Wait {ts} sec...')
    await asyncio.sleep(ts)

    service = kwargs['service']
    link = kwargs['link']
    df_mini_pattern = kwargs['df_mini_pattern']
    df_mini_criteria = kwargs['df_mini_criteria']
    ss_id = kwargs['ss_id']
    project = kwargs['project']

    try:
        status = await asyncio.wait_for(
            async_func(service, link, df_mini_pattern, df_mini_criteria, ss_id, project), timeout=timeout)

        if status:  # Если статус истинен
            await fix_error(service, project, link, str(status))
            return status

    except asyncio.TimeoutError as TE:
        await fix_error(service, project, link, f"TimeOut {TE}")
        print(f"Error TE: Задача была отменена из-за таймаута. {TE}")
        traceback.print_exc()
        return None

    except Exception as Ex:  # Обработка других исключений
        await fix_error(service, project, link, f"Error TOO Ex: {Ex}")
        print(f"Error TOO Ex: {Ex}")
        traceback.print_exc()
        return None

async def time_out_play(async_func, timeout=180, **kwargs):
    ts = random.randint(5, max_sec)
    print(f'Wait {ts} sec...')
    await asyncio.sleep(ts)

    service = kwargs['service']
    link = kwargs['link']
    df_mini_pattern = kwargs['df_mini_pattern']
    df_mini_criteria = kwargs['df_mini_criteria']
    ss_id = kwargs['ss_id']
    project = kwargs['project']

    playwright, browser, page = await get_playwright(link)
    if not page:
        return None, None, None

    status = None

    try:
        status = await asyncio.wait_for(
            async_func(service, link, df_mini_pattern, df_mini_criteria, ss_id, project, playwright, browser, page), timeout=timeout)

        if status:  # Если статус истинен
            await fix_error(service, project, link, str(status))

    except asyncio.TimeoutError as TE:
        await fix_error(service, project, link, f"TimeoutError {TE}")
        print(f"Error PLAY TE: Задача была отменена из-за таймаута. {TE}")
        traceback.print_exc()
        status = None

    except asyncio.CancelledError as CE:
        await fix_error(service, project, link, f"CancelledError {CE}")
        print(f"Error PLAY CE: Задача была отменена из-за таймаута. {CE}")
        traceback.print_exc()
        status = None

    except Exception as Ex:  # Обработка других исключений
        await fix_error(service, project, link, f"Error TOP Ex: {Ex}")
        print(f"Error PLAY Ex: Произошла ошибка: {Ex}")
        traceback.print_exc()
        status = None

    finally:
        if browser:
            await browser.close()
            await playwright.stop()
        print('-- Close browser and playwright is OK!')
        return status

async def start_zoom(service):
    timetable, projects, portal = [], [], []
    #timetable, projects, portal = await get_set()

    local_ip = await get_local_ip()
    print('local_ip', local_ip)

    df = await get_table_scope(service, ss_id, 'zoom')
    #print(df)
    idx_num_row = df.index[df['Проект'] == 'Кол-во строк'].tolist()[0]
    print(idx_num_row)
    df_counts = pd.Series(df.iloc[idx_num_row].values, index=df.columns).reset_index()
    df_counts[0] = pd.to_numeric(df_counts[0], errors='coerce')
    # Удаляем строки с NaN значениями в указанной колонке
    df_counts = df_counts.dropna(subset=[0])
    df_counts = df_counts.sort_values(by=0)
    #print(df_counts)

    list_ = df_counts['index'].to_list()
    print(list_)
    #random.shuffle(list_)

    df_uniq = await get_table_scope(service, ss_id, 'unique_url')

    df_logs = await get_table_scope(service, ss_id, 'logs')
    print(df_logs)

    for project in list_:
        if 'Проект' in project:
            continue

        #-----------------------------------------------------
        # if project not in project_on: #Не берем в работу те у кого не стоит галочка
        #     print(f"Пропускаем - {project}")
        #     continue
        # -----------------------------------------------------

        #Если дата не совпадает с сегодняшней
        host_logs = ''
        filtered_logs = df_logs[df_logs['service_name'] == project]
        if not filtered_logs.empty:
            idx_logs = filtered_logs.index[0]

            #Пропуск по дате
            date_logs = df_logs.loc[idx_logs, 'date']
            if date_logs == current_date:
                #print()
                continue

            #Пропуск по IP
            host_logs = df_logs.loc[idx_logs, 'reserve']
            if host_logs != local_ip:
                print('Skip:', host_logs, local_ip)
                continue

        else:
            print(f"No logs found for service: {project}")

        #project = 'AlphaPet'

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
        random.shuffle(df_link_list)

        len_df = len(df_link_list)
        print(f'\n========================= Project = {project} = Len ({len_df})==============================')

        start_time = time.time()
        list_links = []
        black_list = []

        for idx, link in enumerate(df_link_list):
            left = len_df - df_link_list.index(link)
            print(f'\n*************************{idx}*({left})*[{host_logs}]**************************\n----------------- {link} ----------------')

            #link = row[project]
            #---------------------------------------------------------------------------------------------------------
            if 'pravda-sotrudnikov.ru' in link:
                pattern = r'company/([^/]+)/'

                company = await extract_company_name(pattern, link) #Наименование компании в pravda-sotrudnikov.ru
                if company in list_links:
                    print('Ссылка уже проверена.')
                    continue
                else:
                    list_links.append(company)

                # status = await check_pravda(service, company, df_mini_pattern, df_mini_criteria, ss_id, project)
                # if status:
                #     await fix_error(service, link, str(status))

                status = await time_out_on(check_pravda,
                                           service=service,
                                           link=company,
                                           df_mini_pattern=df_mini_pattern,
                                           df_mini_criteria=df_mini_criteria,
                                           ss_id=ss_id,
                                           project=project)
                # if status:
                #     black_list.append('pravda-sotrudnikov.ru')

            # ---------------------------------------------------------------------------------------------------------
            elif 'ocompanii' in link:
                #link = 'https://ocompanii.net/company/information.php?cid=764047'
                top_df = df_uniq[(df_uniq['project'] == project) & (df_uniq['url'] == link)].reset_index(drop=True)
                if not top_df.empty:
                    print('Есть общая ссылка на статью')
                    link = top_df.loc[0, 'top_url']

                if link in list_links:
                    print('Ссылка уже проверена.')
                    continue

                else:
                    list_links.append(link)

                status = await time_out_on(check_ocompanii,
                                           service=service,
                                           link=link,
                                           df_mini_pattern=df_mini_pattern,
                                           df_mini_criteria=df_mini_criteria,
                                           ss_id=ss_id,
                                           project=project)
                # if status:
                #     black_list.append('ocompanii')

            #---------------------------------------------------------------------------------------------------------
            elif 'dreamjob.ru' in link:
                pattern = r'(https://dreamjob\.ru/employers/\d+)'
                link_company = await extract_company_name(pattern, link)
                if link_company in list_links:
                    print('Ссылка уже проверена.')
                    continue

                else:
                    list_links.append(link_company)

                # status = await check_dreamjob(service, link_company, df_mini_pattern, df_mini_criteria, ss_id, project)
                # if status:
                #     await fix_error(service, link, str(status))

                status = await time_out_on(check_dreamjob,
                                           service=service,
                                           link=link_company,
                                           df_mini_pattern=df_mini_pattern,
                                           df_mini_criteria=df_mini_criteria,
                                           ss_id=ss_id,
                                           project=project)
                # if status:
                #     black_list.append('dreamjob.ru')

            #---------------------------------------------------------------------------------------------------------
            elif '2gis.ru' in link:
                top_df = df_uniq[(df_uniq['project'] == project) & (df_uniq['url'] == link)].reset_index(drop=True)

                if not top_df.empty:
                    print('Есть общая ссылка на статью')
                    link = top_df.loc[0, 'top_url']

                if link in list_links:
                    print('Ссылка уже проверена.')
                    continue

                else:
                    list_links.append(link)

                status = await time_out_on(check_2gis,
                                           service=service,
                                           link=link,
                                           df_mini_pattern=df_mini_pattern,
                                           df_mini_criteria=df_mini_criteria,
                                           ss_id=ss_id,
                                           project=project)


            # ---------------------------------------------------------------------------------------------------------
            elif 'sravni.ru' in link:
                top_df = df_uniq[(df_uniq['project'] == project) & (df_uniq['url'] == link)].reset_index(drop=True)

                if not top_df.empty:
                    print('Есть общая ссылка на статью')
                    link = top_df.loc[0, 'top_url']

                if link in list_links:
                    print('Ссылка уже проверена.')
                    continue

                else:
                    list_links.append(link)

                pattern = r'https://www\.sravni\.ru/(.*?)/otzyvy/'
                link_company = await extract_company_name(pattern, link)

                if not link_company:
                    continue

                link = f"https://www.sravni.ru/{link_company}/otzyvy/"

                if link in list_links:
                    print('Ссылка уже проверена.')
                    continue

                else:
                    list_links.append(link)

                await time_out_on(check_sravni,
                                           service=service,
                                           link=link,
                                           df_mini_pattern=df_mini_pattern,
                                           df_mini_criteria=df_mini_criteria,
                                           ss_id=ss_id,
                                           project=project)


            # ---------------------------------------------------------------------------------------------------------
            elif 'drive2.ru' in link:
                if link in list_links:
                    print('Ссылка уже проверена.')
                    continue

                else:
                    list_links.append(link)

                status = await time_out_on(check_drive2,
                                           service=service,
                                           link=link,
                                           df_mini_pattern=df_mini_pattern,
                                           df_mini_criteria=df_mini_criteria,
                                           ss_id=ss_id,
                                           project=project)
                # if status:
                #     black_list.append('drive2.ru')

            #---------------------------------------------------------------------------------------------------------
            elif 'irecommend_off' in link:
                top_df = df_uniq[(df_uniq['project'] == project) & (df_uniq['url'] == link)].reset_index(drop=True)
                #print(top_df)

                if not top_df.empty:
                    print('Есть общая ссылка на статью')
                    link = top_df.loc[0, 'top_url']

                if link in list_links:
                    print('Ссылка уже проверена.')
                    continue

                else:
                    list_links.append(link)

                status = await time_out_on(check_irecommend,
                                           service=service,
                                           link=link,
                                           df_mini_pattern=df_mini_pattern,
                                           df_mini_criteria=df_mini_criteria,
                                           ss_id=ss_id,
                                           project=project)
                # if status:
                #     black_list.append('irecommend')

            #---------------------------------------------------------------------------------------------------------
            elif 'otzovik.com' in link:

                top_df = df_uniq[(df_uniq['project'] == project) & (df_uniq['url'] == link)].reset_index(drop=True)
                #print(top_df)

                if not top_df.empty:
                    print('Есть общая ссылка на статью')
                    link = top_df.loc[0, 'top_url']

                if link in list_links:
                    print('Ссылка уже проверена.')
                    continue

                else:
                    list_links.append(link)

                await time_out_play(check_otzovik,
                                           service=service,
                                           link=link,
                                           df_mini_pattern=df_mini_pattern,
                                           df_mini_criteria=df_mini_criteria,
                                           ss_id=ss_id,
                                           project=project)


            #---------------------------------------------------------------------------------------------------------
            elif 'dzen.ru' in link:
                if link in list_links:
                    print('Ссылка уже проверена.')
                    continue

                else:
                    list_links.append(link)

                status = await time_out_play(check_dzen,
                                           service=service,
                                           link=link,
                                           df_mini_pattern=df_mini_pattern,
                                           df_mini_criteria=df_mini_criteria,
                                           ss_id=ss_id,
                                           project=project)
                # if status:
                #     black_list.append('youtube')

            # ---------------------------------------------------------------------------------------------------------
            elif 'youtube' in link:
                if link in list_links:
                    print('Ссылка уже проверена.')
                    continue

                else:
                    list_links.append(link)

                # status = await check_youtube(service, link, df_mini_pattern, df_mini_criteria, ss_id, project)
                # if status:
                #     await fix_error(service, link, str(status))

                status = await time_out_play(check_youtube,
                                           service=service,
                                           link=link,
                                           df_mini_pattern=df_mini_pattern,
                                           df_mini_criteria=df_mini_criteria,
                                           ss_id=ss_id,
                                           project=project)
                # if status:
                #     black_list.append('youtube')

            #---------------------------------------------------------------------------------------------------------
            elif 'aplaut.io' in link:
                link = 'https://app.aplaut.io/b/reviews'
                if link in list_links:
                    print('Ссылка уже проверена.')
                    continue

                else:
                    list_links.append(link)

                # status = await check_aplout(service, link, df_mini_pattern, df_mini_criteria, ss_id, project)
                # if status:
                #     await fix_error(service, link, str(status))

                status = await time_out_on(check_aplout,
                                           service=service,
                                           link=link,
                                           df_mini_pattern=df_mini_pattern,
                                           df_mini_criteria=df_mini_criteria,
                                           ss_id=ss_id,
                                           project=project)
                # if status:
                #     black_list.append('aplaut.io')

            #---------------------------------------------------------------------------------------------------------
            elif 'yandex.ru/maps' in link:

                top_df = df_uniq[(df_uniq['project'] == project) & (df_uniq['url'] == link)].reset_index(drop=True)
                #print(top_df)

                if not top_df.empty:
                    print('Есть общая ссылка на статью')
                    link = top_df.loc[0, 'top_url']

                link_split = link.split('/')

                for lnk in link_split:
                    if lnk.isdigit():
                        try:
                            idx = link_split.index(lnk)
                            #print(link_split)
                            #print(idx, lnk)
                            link_company = os.path.join('https://yandex.ru/maps/org', lnk, 'reviews')

                        except:
                            continue

                if link_company in list_links:
                    print('Ссылка уже проверена.')
                    continue

                else:
                    list_links.append(link_company)

                status = await time_out_play(check_ya,
                                           service=service,
                                           link=link_company,
                                           df_mini_pattern=df_mini_pattern,
                                           df_mini_criteria=df_mini_criteria,
                                           ss_id=ss_id,
                                           project=project)
                # if status:
                #     black_list.append('yandex.ru/maps')

            # ---------------------------------------------------------------------------------------------------------
            elif 'otvet.mail' in link:
                if black_list:
                    if any(black in link for black in black_list):
                        continue

                top_df = df_uniq[(df_uniq['project'] == project) & (df_uniq['url'] == link)].reset_index(drop=True)
                #print(top_df)

                if not top_df.empty:
                    print('Есть общая ссылка на статью')
                    link = top_df.loc[0, 'top_url']

                if link in list_links:
                    print('Ссылка уже проверена.')
                    continue

                else:
                    list_links.append(link)

                status = await time_out_play(check_otvet,
                                           service=service,
                                           link=link,
                                           df_mini_pattern=df_mini_pattern,
                                           df_mini_criteria=df_mini_criteria,
                                           ss_id=ss_id,
                                           project=project)
                # if status:
                #     black_list.append('otvet.mail')

            # ---------------------------------------------------------------------------------------------------------
            elif 'market.yandex' in link:
                if link in list_links:
                    print('Ссылка уже проверена.')
                    continue

                else:
                    list_links.append(link)

                status = await time_out_play(check_ya_market,
                                           service=service,
                                           link=link,
                                           df_mini_pattern=df_mini_pattern,
                                           df_mini_criteria=df_mini_criteria,
                                           ss_id=ss_id,
                                           project=project)
                # if status:
                #     black_list.append('market.yandex')

            #---------------------------------------------------------------------------------------
            elif 'rustore.ru' in link:
                if link in list_links:
                    print('Ссылка уже проверена.')
                    continue

                else:
                    list_links.append(link)

                await time_out_play(check_rustore,
                                             service=service,
                                             link=link,
                                             df_mini_pattern=df_mini_pattern,
                                             df_mini_criteria=df_mini_criteria,
                                             ss_id=ss_id,
                                             project=project)

                #--------------------------------------------------------------------
            elif 'rocketdata' in link:
                link = 'https://go.rocketdata.io/reviews-management/reviews?ordering=-creation_date'
                if link in list_links:
                    print('Ссылка уже проверена.')
                    continue

                else:
                    list_links.append(link)

                await time_out_on(check_rocketdata,
                                             service=service,
                                             link=link,
                                             df_mini_pattern=df_mini_pattern,
                                             df_mini_criteria=df_mini_criteria,
                                             ss_id=ss_id,
                                             project=project)

            # ---------------------------------------------------------------------------------------------------------
            # elif 'vk.com' in link:
            #     print(link)
            #     if 'wall' in link:
            #         pattern = r'(https?://vk\.com/wall-\d+_\d+)'
            #         link_company = await extract_company_name(pattern, link)
            #
            #     elif '?w=' in link:
            #         edit_link = link.split("?w=")
            #         link_company = "http://vk.com/" + edit_link[-1]
            #
            #     else:
            #         link_company = link
            #
            #     print("link_company =", link_company)
            #
            #     if link_company in list_links:
            #         continue
            #
            #     else:
            #         list_links.append(link_company)
            #
            #     status = await time_out_play(check_vk,
            #                                service=service,
            #                                link=link_company,
            #                                df_mini_pattern=df_mini_pattern,
            #                                df_mini_criteria=df_mini_criteria,
            #                                ss_id=ss_id,
            #                                project=project)
            #     if status:
            #         black_list.append('vk.com')

        finish_sec = time.time() - start_time
        datas = {'service_name': project,
                'count': len_df,
                'date': current_date,
                 'time': finish_sec}

        await write_log_sheet(service, ss_id, 'logs', datas)

async def main_zoom():
    service = await get_service()
    await start_zoom(service)

if "__main__" in __name__:
    asyncio.run(main_zoom())