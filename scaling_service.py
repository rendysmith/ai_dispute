import os.path
import time

import asyncio
import re
import random

from portals.portal_aplaut import check_aplout
from portals.portal_ya_market import check_ya_market
from utils.gs_editor import get_service, get_table_scope, append_data_to_sheet_scope, write_log_sheet
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

from utils.constants import TABLES_LIST

ss_id = TABLES_LIST['zoom']

async def extract_company_name(pattern, url):
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    else:
        return None

async def fix_error(service, portal, error):
    data = {
        'date': time.ctime(),
        'portal': portal,
        'error': error,
    }

    tab_name = 'ERRORS'
    await append_data_to_sheet_scope(service, ss_id, tab_name, data)

async def start_zoom(service):
    df = await get_table_scope(service, ss_id, 'zoom')
    #print(df)

    list_ = list(df)
    random.shuffle(list_)

    for project in list_:
        if 'Проект' in project:
            continue

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
        print(f'========================= Project = {project} = Len ({len_df})==============================')

        list_links = []

        for idx, link in enumerate(df_link_list):

            left = len_df - df_link_list.index(link)
            print(f'*************************{idx}*({left})***************************')

            #link = row[project]
            #---------------------------------------------------------------------------------------------------------
            if 'pravda-sotrudnikov.ru' in link:
                pattern = r'company/([^/]+)/'

                company = await extract_company_name(pattern, link) #Наименование компании в pravda-sotrudnikov.ru
                if company in list_links:
                    continue
                else:
                    list_links.append(company)

                status = await check_pravda(service, company, df_mini_pattern, df_mini_criteria, ss_id, project)
                if status:
                    await fix_error(service, link, str(status))

            # ---------------------------------------------------------------------------------------------------------
            elif 'ocompanii' in link:
                link = 'https://ocompanii.net/company/information.php?cid=764047'
                if link in list_links:
                    continue

                else:
                    list_links.append(link)
                    print(len(list_links))

                status = await check_ocompanii(service, link, df_mini_pattern, df_mini_criteria, ss_id, project)
                if status:
                    await fix_error(service, link, str(status))

            #---------------------------------------------------------------------------------------------------------
            elif 'dreamjob.ru' in link:
                pattern = r'(https://dreamjob\.ru/employers/\d+)'
                link_company = await extract_company_name(pattern, link)
                if link_company in list_links:
                    continue

                else:
                    list_links.append(link_company)

                status = await check_dreamjob(service, link_company, df_mini_pattern, df_mini_criteria, ss_id, project)
                if status:
                    await fix_error(service, link, str(status))

            #---------------------------------------------------------------------------------------------------------
            elif '2gis' in link:
                if link in list_links:
                    continue

                else:
                    list_links.append(link)

                status = await check_2gis(service, link, df_mini_pattern, df_mini_criteria, ss_id, project)
                if status:
                    await fix_error(service, link, str(status))

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

                status = await check_sravni(service, link, df_mini_pattern, df_mini_criteria, ss_id, project)
                if status:
                    await fix_error(service, link, str(status))

            # ---------------------------------------------------------------------------------------------------------
            elif 'drive2.ru' in link:
                if link in list_links:
                    continue

                else:
                    list_links.append(link)

                status = await check_drive2(service, link, df_mini_pattern, df_mini_criteria, ss_id, project)
                if status:
                    await fix_error(service, link, str(status))

            # ---------------------------------------------------------------------------------------------------------
            elif 'vk.com' in link:
                print(link)
                if 'wall' in link:
                    pattern = r'(https?://vk\.com/wall-\d+_\d+)'
                    link_company = await extract_company_name(pattern, link)

                elif '?w=' in link:
                    edit_link = link.split("?w=")
                    link_company = "http://vk.com/" + edit_link[-1]

                print("link_company =", link_company)

                if link_company in list_links:
                    continue

                else:
                    list_links.append(link_company)

                status = await check_vk(service, link_company, df_mini_pattern, df_mini_criteria, ss_id, project)
                if status:
                    await fix_error(service, link, str(status))

            #---------------------------------------------------------------------------------------------------------
            elif 'irecommend' in link:
                if link in list_links:
                    continue

                else:
                    list_links.append(link)

                print('irecommend Бывают баны по IP')
                status = await check_irecommend(service, link, df_mini_pattern, df_mini_criteria, ss_id, project)
                if status:
                    print(status)
                    await fix_error(service, link, str(status))

            #---------------------------------------------------------------------------------------------------------
            elif 'otzovik.com' in link:
                if link in list_links:
                    continue

                else:
                    list_links.append(link)

                print('otzovik Бывают баны по IP')

                status = await check_otzovik(service, link, df_mini_pattern, df_mini_criteria, ss_id, project)
                if status:
                    await fix_error(service, link, str(status))

            #---------------------------------------------------------------------------------------------------------
            elif 'dzen.ru' in link:
                if link in list_links:
                    continue

                else:
                    list_links.append(link)

                status = await check_dzen(service, link, df_mini_pattern, df_mini_criteria, ss_id, project)
                if status:
                    await fix_error(service, link, str(status))

            #---------------------------------------------------------------------------------------------------------
            elif 'aplaut.io' in link:
                link = 'https://app.aplaut.io/b/reviews'
                if link in list_links:
                    continue

                else:
                    list_links.append(link)

                status = await check_aplout(service, link, df_mini_pattern, df_mini_criteria, ss_id, project)
                if status:
                    await fix_error(service, link, str(status))

            #---------------------------------------------------------------------------------------------------------
            elif 'yandex.ru/maps' in link:
                link_split = link.split('/')
                for lnk in link_split:
                    if lnk.isdigit():
                        try:
                            idx = link_split.index(lnk)
                            print(link_split)
                            print(idx, lnk)
                            link_company = os.path.join('https://yandex.ru/maps/org', lnk, 'reviews')

                        except:
                            continue

                if link_company in list_links:
                    continue

                else:
                    list_links.append(link_company)

                status = await check_ya(service, link_company, df_mini_pattern, df_mini_criteria, ss_id, project)
                if status:
                    await fix_error(service, link, str(status))

            # ---------------------------------------------------------------------------------------------------------
            elif 'otvet.mail' in link:
                if link in list_links:
                    continue

                else:
                    list_links.append(link)

                status = await check_otvet(service, link, df_mini_pattern, df_mini_criteria, ss_id, project)
                if status:
                    await fix_error(service, link, str(status))

            # ---------------------------------------------------------------------------------------------------------
            elif 'market.yandex' in link:
                if link in list_links:
                    continue

                else:
                    list_links.append(link)

                status = await check_ya_market(service, link, df_mini_pattern, df_mini_criteria, ss_id, project)
                if status:
                    await fix_error(service, link, str(status))




        data = {'service_name': project, 'date': time.ctime()}
        await write_log_sheet(service, ss_id, 'logs', data)

async def main_zoom():
    service = await get_service()
    await start_zoom(service)

if "__main__" in __name__:
    asyncio.run(main_zoom())