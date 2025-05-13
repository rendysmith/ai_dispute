import asyncio
import os.path
import random
import time
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

from portals.dreamjob import check_dreamjob
from portals.ocompanii import check_ocompanii
from portals.portal_2gis import check_2gis
from portals.portal_aplaut import check_aplout
from portals.portal_drive2 import check_drive2
from portals.portal_dzen import check_dzen
from portals.portal_ingate import check_ingate
from portals.portal_otvet import check_otvet
from portals.portal_rustore import check_rustore
from portals.portal_sravni import check_sravni
from portals.portal_ya_market import check_ya_market
from portals.pravda_sotrudnikov import check_pravda
from portals.rocketdata import check_rocketdata
from portals.youtube import check_youtube

from utils.central_module import get_local_ip, time_out_on, time_out_sel
from utils.constants import TABLES_LIST
from utils.converter import extract_company_name
from utils.gs_editor import get_service, get_table_scope, write_log_sheet

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

max_sec = int(os.environ.get("MAX_SEC"))

ss_id = TABLES_LIST['zoom']
current_date = datetime.now().strftime("%d.%m.%Y")

async def start_zoom(service):
    timetable, projects, portal = [], [], []
    #timetable, projects, portal = await get_set()

    local_ip = await get_local_ip()
    print('local_ip ScalS', local_ip)

    df = await get_table_scope(service, ss_id, 'zoom')
    #print(df)
    idx_num_row = df.index[df['Проект'] == 'Кол-во строк'].tolist()[0]
    print(f"ROW of COUNT: {idx_num_row}")

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
        print(f'+++++++++++++++++ {project} +++++++++++++++++++++')
        #Исключить проекты
        if any(prj == project for prj in ['Проект', 'AlphaPet']):
            print(f'--- Skip: {project}')
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

        df_mini_prj = df[["Проект", project]]
        df_mini_pattern = [row[project] for ind, row in df_mini_prj.iterrows() if "Пример реакции" in row['Проект']]
        df_mini_criteria = [row[project] for ind, row in df_mini_prj.iterrows() if "Особые критерии" in row['Проект']]

        df_mini = df[project]
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

        links = await pars_url(service, ss_id, project)

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
                                           project=project,
                                           links=links)
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
                                           project=project,
                                           links=links)
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
                                           project=project,
                                           links=links)
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
                                           project=project,
                                           links=links)


            # ---------------------------------------------------------------------------------------------------------
            elif 'sravni.ru_off' in link:
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
                                           project=project, links=links)


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
                                           project=project,
                                           links=links)
                # if status:
                #     black_list.append('drive2.ru')




            #---------------------------------------------------------------------------------------------------------
            elif 'dzen.ru' in link:
                if link in list_links:
                    print('Ссылка уже проверена.')
                    continue

                else:
                    list_links.append(link)

                await time_out_sel(check_dzen,
                                           service=service,
                                           link=link,
                                           df_mini_pattern=df_mini_pattern,
                                           df_mini_criteria=df_mini_criteria,
                                           ss_id=ss_id,
                                           project=project,
                                   links=links)
                # if status:
                #     black_list.append('youtube')

            # ---------------------------------------------------------------------------------------------------------
            elif 'youtube' in link:
                if link in list_links:
                    print('Ссылка уже проверена.')
                    continue

                else:
                    list_links.append(link)

                await check_youtube(service, link, df_mini_pattern, df_mini_criteria, ss_id, project, links)

            #----------------------------------------------------------------------------------------------------------
            elif 'ingate' in link:
                link = 'https://pntr.ingate.ru'
                if link in list_links:
                    print('Ссылка уже проверена.')
                    continue

                else:
                    list_links.append(link)

                await check_ingate(service, link, df_mini_pattern, df_mini_criteria, ss_id, project, links)


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
                                           project=project, links=links)
                # if status:
                #     black_list.append('aplaut.io')

            #---------------------------------------------------------------------------------------------------------
            # elif 'yandex.ru/maps' in link or 'yandex.ru/web-maps' in link:
            #
            #     top_df = df_uniq[(df_uniq['project'] == project) & (df_uniq['url'] == link)].reset_index(drop=True)
            #     #print(top_df)
            #
            #     if not top_df.empty:
            #         print('Есть общая ссылка на статью')
            #         link = top_df.loc[0, 'top_url']
            #
            #     link_split = link.split('/')
            #     for lnk in link_split:
            #         if lnk.isdigit():
            #             try:
            #                 #idx = link_split.index(lnk)
            #                 #print(link_split)
            #                 #print(idx, lnk)
            #                 link_company = os.path.join('https://yandex.ru/maps/org', lnk, 'reviews')
            #                 print('-- cut link:', link_company)
            #
            #             except:
            #                 continue
            #
            #     if link_company in list_links:
            #         print('Ссылка уже проверена.')
            #         continue
            #
            #     else:
            #         list_links.append(link_company)
            #
            #     status = await time_out_play(check_ya,
            #                                service=service,
            #                                link=link_company,
            #                                df_mini_pattern=df_mini_pattern,
            #                                df_mini_criteria=df_mini_criteria,
            #                                ss_id=ss_id,
            #                                project=project)
            #     # if status:
            #     #     black_list.append('yandex.ru/maps')

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

                await time_out_on(check_otvet,
                                           service=service,
                                           link=link,
                                           df_mini_pattern=df_mini_pattern,
                                           df_mini_criteria=df_mini_criteria,
                                           ss_id=ss_id,
                                           project=project, links=links)
                # if status:
                #     black_list.append('otvet.mail')

            # ---------------------------------------------------------------------------------------------------------
            elif 'market.yandex' in link:
                if link in list_links:
                    print('Ссылка уже проверена.')
                    continue

                else:
                    list_links.append(link)

                await time_out_sel(check_ya_market,
                                           service=service,
                                           link=link,
                                           df_mini_pattern=df_mini_pattern,
                                           df_mini_criteria=df_mini_criteria,
                                           ss_id=ss_id,
                                           project=project, links=links)
                # if status:
                #     black_list.append('market.yandex')
            #---------------------------------------------------------------------------------------
            elif 'rustore.ru' in link:
                if link in list_links:
                    print('Ссылка уже проверена.')
                    continue

                else:
                    list_links.append(link)

                await time_out_sel(check_rustore,
                                             service=service,
                                             link=link,
                                             df_mini_pattern=df_mini_pattern,
                                             df_mini_criteria=df_mini_criteria,
                                             ss_id=ss_id,
                                             project=project, links=links)

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
                                             project=project, links=links)

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

            #---------------------------------------------------------------------------------------------------------
            # elif 'irecommend_off' in link:
            #     top_df = df_uniq[(df_uniq['project'] == project) & (df_uniq['url'] == link)].reset_index(drop=True)
            #     #print(top_df)
            #
            #     if not top_df.empty:
            #         print('Есть общая ссылка на статью')
            #         link = top_df.loc[0, 'top_url']
            #
            #     if link in list_links:
            #         print('Ссылка уже проверена.')
            #         continue
            #
            #     else:
            #         list_links.append(link)
            #
            #     await time_out_play(check_irecommend,
            #                                service=service,
            #                                link=link,
            #                                df_mini_pattern=df_mini_pattern,
            #                                df_mini_criteria=df_mini_criteria,
            #                                ss_id=ss_id,
            #                                project=project)
            #     # if status:
            #     #     black_list.append('irecommend')
            #
            # #---------------------------------------------------------------------------------------------------------
            # elif 'otzovik.com_off' in link:
            #
            #     top_df = df_uniq[(df_uniq['project'] == project) & (df_uniq['url'] == link)].reset_index(drop=True)
            #     #print(top_df)
            #
            #     if not top_df.empty:
            #         print('Есть общая ссылка на статью')
            #         link = top_df.loc[0, 'top_url']
            #
            #     if link in list_links:
            #         print('Ссылка уже проверена.')
            #         continue
            #
            #     else:
            #         list_links.append(link)
            #
            #     await time_out_play(check_otzovik,
            #                                service=service,
            #                                link=link,
            #                                df_mini_pattern=df_mini_pattern,
            #                                df_mini_criteria=df_mini_criteria,
            #                                ss_id=ss_id,
            #                                project=project)

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