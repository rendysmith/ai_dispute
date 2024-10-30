import asyncio
import os
import random

import time

from datetime import datetime, timedelta

import pandas as pd

from dotenv import load_dotenv

from utils.central_module import get_local_ip, wait_for_portal
from utils.constants import TABLES_LIST, platforms
from utils.gs_editor import get_service, get_table_scope, write_log_sheet
from utils.user_agent import get_selenium_proxy

from portals.portal_otzovik import check_otzovik
from portals.irecommend import check_irecommend
from portals.portal_ya import check_ya

current_date = datetime.now()
record_date = current_date.strftime("%d.%m.%Y")

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)
days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))
ss_id = TABLES_LIST['zoom']

async def main_scaling():
    local_ip = await get_local_ip()
    print('local_ip', local_ip)

    service = await get_service()
    df = await get_table_scope(service, ss_id, 'zoom')
    #print(df)
    idx_num_row = df.index[df['Проект'] == 'Кол-во строк'].tolist()[0]
    #print(idx_num_row)
    df_counts = pd.Series(df.iloc[idx_num_row].values, index=df.columns).reset_index()
    df_counts[0] = pd.to_numeric(df_counts[0], errors='coerce')
    # Удаляем строки с NaN значениями в указанной колонке
    df_counts = df_counts.dropna(subset=[0])
    df_counts = df_counts.sort_values(by=0)
    #print(df_counts)

    list_ = df_counts['index'].to_list()
    #print(list_)
    #random.shuffle(list_)

    df_uniq = await get_table_scope(service, ss_id, 'unique_url')

    df_logs = await get_table_scope(service, ss_id, 'logs')
    #print(df_logs)

    driver = await get_selenium_proxy()

    for project in list_:
        if 'Проект' in project:
            continue

        for platform, web  in platforms.items():
            print(f'+++++++++++++++++++++++++++++++{project} {platform} {web}+++++++++++++++++++++++++++++++++++++')
            #Если дата не совпадает с сегодняшней
            host_logs = ''
            project_platform = f'{project}_{platform}'
            filtered_logs = df_logs[df_logs['service_name'] == project_platform]
            if not filtered_logs.empty:
                idx_logs = filtered_logs.index[0]

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

            irec_link = [i for i in df_link_list if any(w in i for w in web)]
            #print(irec_link)
            len_irec = len(irec_link)
            print('Len links', len_irec)

            if len_irec == 0:
                continue

            random.shuffle(df_link_list)

            len_df = len(df_link_list)
            print(f'\n========================= Project = {project} = Len ({len_df})==============================')

            start_time = time.time()
            list_links = []

            record = False
            for idx, link in enumerate(df_link_list):
                left = len_df - df_link_list.index(link)
                print(
                    f'\n*************************{idx}*({left})*{project}**************************\n----------------- {link} ----------------')
                status = True

                if 'irecommend' in link:
                    record = True
                    top_df = df_uniq[(df_uniq['project'] == project) & (df_uniq['url'] == link)].reset_index(drop=True)
                    # print(top_df)

                    if not top_df.empty:
                        print('Есть общая ссылка на статью')
                        link = top_df.loc[0, 'top_url']

                    if link in list_links:
                        print('Ссылка уже проверена.')
                        continue

                    else:
                        list_links.append(link)

                    status = await check_irecommend(service=service,
                                           link=link,
                                           pattern=df_mini_pattern,
                                           criteria=df_mini_criteria,
                                           ss_id=ss_id,
                                           project=project,
                                           driver=driver)

                elif 'otzovik' in link:
                    record = True
                    top_df = df_uniq[(df_uniq['project'] == project) & (df_uniq['url'] == link)].reset_index(drop=True)
                    # print(top_df)

                    if not top_df.empty:
                        print('Есть общая ссылка на статью')
                        link = top_df.loc[0, 'top_url']

                    if link in list_links:
                        print('Ссылка уже проверена.')
                        continue

                    else:
                        list_links.append(link)

                    status = await check_otzovik(service=service,
                                                 link=link,
                                                 pattern=df_mini_pattern,
                                                 criteria=df_mini_criteria,
                                                 ss_id=ss_id,
                                                 project=project,
                                                 driver=driver)

                elif 'yandex.ru/maps' in link or 'yandex.ru/web-maps' in link:
                    top_df = df_uniq[(df_uniq['project'] == project) & (df_uniq['url'] == link)].reset_index(drop=True)
                    #print(top_df)

                    if not top_df.empty:
                        print('Есть общая ссылка на статью')
                        link = top_df.loc[0, 'top_url']

                    link_split = link.split('/')
                    for lnk in link_split:
                        if lnk.isdigit():
                            try:
                                link_company = os.path.join('https://yandex.ru/maps/org', lnk, 'reviews')
                                print('-- cut link:', link_company)

                            except:
                                continue

                    if link_company in list_links:
                        print('Ссылка уже проверена.')
                        continue

                    else:
                        list_links.append(link_company)

                    status = await check_ya(service=service,
                                            link=link_company,
                                            pattern=df_mini_pattern,
                                            criteria=df_mini_criteria,
                                            ss_id=ss_id,
                                            project=project,
                                            driver=driver)

                if not status:
                    driver.quit()
                    driver = await get_selenium_proxy()

            if record:
                finish_sec = time.time() - start_time
                datas = {'service_name': project_platform,
                        'count': len_irec,
                        'date': record_date,
                        'time': finish_sec}

                print('datas', datas)
                await write_log_sheet(service, ss_id, 'logs', datas)

    driver.close()

async def tst_main():
    url = 'https://irecommend.ru/content/lechenie-v-turtsii-v-odnoi-iz-luchshikh-klinik-v-kotorykh-ya-kogda-libo-byla-tak-zhe-strakho'
    url = 'https://irecommend.ru/content/strakhovka-rabotaet'
    url = 'https://irecommend.ru/content/idealnyi-sostav-imenno-takuyu-i-iskala'
    driver = await get_selenium_proxy(url, headless=False)
    await check_irecommend(1, url, 1, 1, 1, 1, driver)


if "__main__" in __name__:
    #asyncio.run(tst_main())
    asyncio.run(main_scaling())



