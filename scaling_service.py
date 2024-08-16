import os.path

import pandas as pd
import asyncio
import re
import itertools
import random

from utils.gs_editor import get_service, get_table_scope
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

async def extract_company_name(pattern, url):
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    else:
        return None

async def main():
    service = await get_service()

    ss_id = '1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w'
    df = await get_table_scope(service, ss_id, 'zoom')
    #print(df)

    list_ = list(df)
    #print(list_)

    for project in list_:
        if 'Проект' in project:
            continue

        print(f'========================= Project = {project} ===============================')

        df_mini = df[project]
        #print(len(df_mini))

        df_mini_pattern = df_mini[df_mini.str.contains('Пример реакции', na=False)]
        df_mini_criteria = df_mini[df_mini.str.contains('Особые критерии', na=False)]

        # Filter rows that contain 'http://'
        df_mini = df_mini[df_mini.str.contains('http', na=False)]

        # Remove duplicates
        # Удаляем дубликаты
        df_mini = df_mini.drop_duplicates().reset_index()
        #print(df_mini)
        # Сортируем строки в колонке project
        #df_mini = df_mini.sort_values().reset_index()

        df_link_list = df_mini[project].to_list()
        random.shuffle(df_link_list)

        #print(df_link_list)
        #input('**********************************************************')
        list_links = []

        for link in df_link_list:
            #link = row[project]
            #---------------------------------------------------------------------------------------------------------
            if 'pravda-sotrudnikov.ru' in link:
                pattern = r'company/([^/]+)/'

                company = await extract_company_name(pattern, link) #Наименование компании в pravda-sotrudnikov.ru
                if company in list_links:
                    continue
                else:
                    list_links.append(company)
                await check_pravda(service, company, df_mini_pattern, df_mini_criteria, ss_id, project)

            # ---------------------------------------------------------------------------------------------------------
            elif 'ocompanii' in link:
                if link in list_links:
                    continue
                else:
                    list_links.append(link)
                await check_ocompanii(service, link, df_mini_pattern, df_mini_criteria, ss_id, project)

            #---------------------------------------------------------------------------------------------------------
            elif 'dreamjob.ru' in link:
                pattern = r'(https://dreamjob\.ru/employers/\d+)'
                link_company = await extract_company_name(pattern, link)
                if link_company in list_links:
                    continue

                else:
                    list_links.append(link_company)
                await check_dreamjob(service, link_company, df_mini_pattern, df_mini_criteria, ss_id, project)

            #---------------------------------------------------------------------------------------------------------
            elif '2gis' in link:
                if link in list_links:
                    continue

                else:
                    list_links.append(link)
                await check_2gis(service, link, df_mini_pattern, df_mini_criteria, ss_id, project)

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
                await check_sravni(service, link, df_mini_pattern, df_mini_criteria, ss_id, project)

            # ---------------------------------------------------------------------------------------------------------
            elif 'drive2.ru' in link:
                if link in list_links:
                    continue

                else:
                    list_links.append(link)
                await check_drive2(service, link, df_mini_pattern, df_mini_criteria, ss_id, project)

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
                await check_vk(service, link_company, df_mini_pattern, df_mini_criteria, ss_id, project)

            #---------------------------------------------------------------------------------------------------------
            elif 'irecommend' in link:
                if link in list_links:
                    continue

                else:
                    list_links.append(link)
                print('irecommend Бывают баны по IP')
                await check_irecommend(service, link, df_mini_pattern, df_mini_criteria, ss_id, project)

            #---------------------------------------------------------------------------------------------------------
            elif 'otzovik.com' in link:
                if link in list_links:
                    continue

                else:
                    list_links.append(link)

                print('otzovik Бывают баны по IP')
                await check_otzovik(service, link, df_mini_pattern, df_mini_criteria, ss_id, project)

            #---------------------------------------------------------------------------------------------------------
            elif 'dzen.ru' in link:
                if link in list_links:
                    continue

                else:
                    list_links.append(link)

                await check_dzen(service, link, df_mini_pattern, df_mini_criteria, ss_id, project)

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

                await check_ya(service, link_company, df_mini_pattern, df_mini_criteria, ss_id, project)



























if "__main__" in __name__:
    asyncio.run(main())