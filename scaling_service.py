import os.path
import time
import traceback
from datetime import datetime
import requests

import asyncio
import re
import random

import traceback

from portals.portal_aplaut import check_aplout
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
from portals.portal_vk import check_vk
from portals.portal_otvet import check_otvet
from portals.youtube import check_youtube

from utils.gs_editor import get_service, get_table_scope, append_data_to_sheet_scope, write_log_sheet

from utils.constants import TABLES_LIST
from utils.user_agent import get_playwright

ss_id = TABLES_LIST['zoom']
current_date = datetime.now().strftime("%d.%m.%Y")

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

async def extract_company_name(pattern, url):
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    else:
        return None

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
        return None

    except Exception as Ex:  # Обработка других исключений
        await fix_error(service, project, link, f"Error Ex: {Ex}")
        print(f"Error Ex: Произошла ошибка: {Ex}")
        return None

async def time_out_play(async_func, timeout=180, **kwargs):
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
        await fix_error(service, project, link, f"Error Ex: {Ex}")
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
    local_ip = await get_local_ip()
    print('local_ip', local_ip)

    df = await get_table_scope(service, ss_id, 'zoom')
    #print(df)

    list_ = list(df)
    random.shuffle(list_)

    df_uniq = await get_table_scope(service, ss_id, 'unique_url')

    df_logs = await get_table_scope(service, ss_id, 'logs')
    #print(df_logs)

    for project in list_:
        if 'Проект' in project:
            continue

        #Если дата не совпадает с сегодняшней
        filtered_logs = df_logs[df_logs['service_name'] == project]
        if not filtered_logs.empty:
            idx_logs = filtered_logs.index[0]

            #Пропуск по дате
            date_logs = df_logs.loc[idx_logs, 'date']
            if date_logs == current_date:
                print()
                #continue

            #Пропуск по IP
            host_logs = df_logs.loc[idx_logs, 'reserve']
            print(host_logs, local_ip)
            if host_logs != local_ip:
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

        list_links = []
        black_list = []

        for idx, link in enumerate(df_link_list):
            left = len_df - df_link_list.index(link)
            print(f'\n*************************{idx}*({left})***************************\n----------------- {link} ----------------')

            #link = row[project]
            #---------------------------------------------------------------------------------------------------------
            if 'pravda-sotrudnikov.ru' in link:
                pattern = r'company/([^/]+)/'

                company = await extract_company_name(pattern, link) #Наименование компании в pravda-sotrudnikov.ru
                if company in list_links:
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
                if status:
                    black_list.append('pravda-sotrudnikov.ru')

            # ---------------------------------------------------------------------------------------------------------
            elif 'ocompanii' in link:
                link = 'https://ocompanii.net/company/information.php?cid=764047'
                if link in list_links:
                    continue

                else:
                    list_links.append(link)
                    print(len(list_links))

                # status = await check_ocompanii(service, link, df_mini_pattern, df_mini_criteria, ss_id, project)
                # if status:
                #     await fix_error(service, link, str(status))

                status = await time_out_on(check_ocompanii,
                                           service=service,
                                           link=link,
                                           df_mini_pattern=df_mini_pattern,
                                           df_mini_criteria=df_mini_criteria,
                                           ss_id=ss_id,
                                           project=project)
                if status:
                    black_list.append('ocompanii')

            #---------------------------------------------------------------------------------------------------------
            elif 'dreamjob.ru' in link:
                pattern = r'(https://dreamjob\.ru/employers/\d+)'
                link_company = await extract_company_name(pattern, link)
                if link_company in list_links:
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
                if status:
                    black_list.append('dreamjob.ru')

            #---------------------------------------------------------------------------------------------------------
            elif '2gis' in link:
                if black_list:
                    if any(black in link for black in black_list):
                        continue

                top_df = df_uniq[(df_uniq['project'] == project) & (df_uniq['url'] == link)].reset_index(drop=True)
                #print(top_df)

                if not top_df.empty:
                    print('Есть общая ссылка на статью')
                    link = top_df.loc[0, 'top_url']

                if link in list_links:
                    continue

                else:
                    list_links.append(link)

                status = await time_out_play(check_2gis,
                                           service=service,
                                           link=link,
                                           df_mini_pattern=df_mini_pattern,
                                           df_mini_criteria=df_mini_criteria,
                                           ss_id=ss_id,
                                           project=project)
                if status:
                    black_list.append('2gis')

            # ---------------------------------------------------------------------------------------------------------
            elif 'sravni.ru' in link:
                pattern = r'https://www\.sravni\.ru/(.*?)/otzyvy/'

                link_company = await extract_company_name(pattern, link)

                if not link_company:
                    continue

                link = f"https://www.sravni.ru/{link_company}/otzyvy/"

                if link in list_links:
                    continue

                else:
                    list_links.append(link)

                status = await time_out_on(check_sravni,
                                           service=service,
                                           link=link,
                                           df_mini_pattern=df_mini_pattern,
                                           df_mini_criteria=df_mini_criteria,
                                           ss_id=ss_id,
                                           project=project)
                if status:
                    black_list.append('sravni.ru')


            # ---------------------------------------------------------------------------------------------------------
            elif 'drive2.ru' in link:
                if link in list_links:
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
                if status:
                    black_list.append('drive2.ru')

            #---------------------------------------------------------------------------------------------------------
            elif 'irecommend' in link:
                if black_list:
                    if any(black in link for black in black_list):
                        continue

                top_df = df_uniq[(df_uniq['project'] == project) & (df_uniq['url'] == link)].reset_index(drop=True)
                #print(top_df)

                if not top_df.empty:
                    print('Есть общая ссылка на статью')
                    link = top_df.loc[0, 'top_url']

                if link in list_links:
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
                if status:
                    black_list.append('irecommend')

            #---------------------------------------------------------------------------------------------------------
            elif 'otzovik.com' in link:
                if black_list:
                    if any(black in link for black in black_list):
                        continue

                top_df = df_uniq[(df_uniq['project'] == project) & (df_uniq['url'] == link)].reset_index(drop=True)
                #print(top_df)

                if not top_df.empty:
                    print('Есть общая ссылка на статью')
                    link = top_df.loc[0, 'top_url']

                if link in list_links:
                    continue

                else:
                    list_links.append(link)

                print('otzovik Бывают баны по IP')

                status = await time_out_on(check_otzovik,
                                           service=service,
                                           link=link,
                                           df_mini_pattern=df_mini_pattern,
                                           df_mini_criteria=df_mini_criteria,
                                           ss_id=ss_id,
                                           project=project)
                if status:
                    black_list.append('otzovik.com')

            #---------------------------------------------------------------------------------------------------------
            elif 'dzen.ru' in link:
                if link in list_links:
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
                if status:
                    black_list.append('youtube')

            # ---------------------------------------------------------------------------------------------------------
            elif 'youtube' in link:
                if link in list_links:
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
                if status:
                    black_list.append('youtube')

            #---------------------------------------------------------------------------------------------------------
            elif 'aplaut.io' in link:
                link = 'https://app.aplaut.io/b/reviews'
                if link in list_links:
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
                if status:
                    black_list.append('aplaut.io')

            #---------------------------------------------------------------------------------------------------------
            elif 'yandex.ru/maps' in link:
                if black_list:
                    if any(black in link for black in black_list):
                        continue

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
                    continue

                else:
                    list_links.append(link_company)

                # status = await check_ya(service, link_company, df_mini_pattern, df_mini_criteria, ss_id, project)
                # if status:
                #     await fix_error(service, link, str(status))
                #     black_list.append('yandex.ru/maps')

                status = await time_out_play(check_ya,
                                           service=service,
                                           link=link_company,
                                           df_mini_pattern=df_mini_pattern,
                                           df_mini_criteria=df_mini_criteria,
                                           ss_id=ss_id,
                                           project=project)
                if status:
                    black_list.append('yandex.ru/maps')

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
                if status:
                    black_list.append('otvet.mail')

            # ---------------------------------------------------------------------------------------------------------
            elif 'market.yandex' in link and any(black not in link for black in black_list):
                if link in list_links:
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
                if status:
                    black_list.append('market.yandex')

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




        datas = {'service_name': project,
                'count': len_df,
                'date': current_date}

        await write_log_sheet(service, ss_id, 'logs', datas)

async def main_zoom():
    service = await get_service()
    await start_zoom(service)

if "__main__" in __name__:
    asyncio.run(main_zoom())