import pandas as pd
import asyncio
import re

from utils.gs_editor import get_service, get_table_scope
from utils.pravda_sotrudnikov import check_pravda
from utils.dreamjob import check_dreamjob

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
    print(df)

    list_ = list(df)
    print(list_)

    for project in list_:
        if 'Проект' in project:
            continue

        print(f'Project = {project}')

        df_mini = df[project]
        print(len(df_mini))

        df_mini_pattern = df_mini[df_mini.str.contains('Пример реакции', na=False)]
        df_mini_criteria = df_mini[df_mini.str.contains('Особые критерии', na=False)]

        # Filter rows that contain 'http://'
        df_mini = df_mini[df_mini.str.contains('http', na=False)]

        # Remove duplicates
        # Удаляем дубликаты
        df_mini = df_mini.drop_duplicates()

        # Сортируем строки в колонке project
        df_mini = df_mini.sort_values().reset_index()
        print(len(df_mini))

        print(df_mini)
        list_links = []

        for idx, row in df_mini.iterrows():
            link = row[project]

            if 'pravda-sotrudnikov.ru' in link:
                pattern = r'company/([^/]+)/'

                company = await extract_company_name(pattern, link) #Наименование компании в pravda-sotrudnikov.ru
                if company in list_links:
                    continue
                else:
                    list_links.append(company)

                #await check_pravda(service, company, df_mini_pattern, df_mini_criteria, ss_id, project)

            elif 'dreamjob.ru' in link:
                pattern = r'(https://dreamjob\.ru/employers/\d+)'
                link_company = await extract_company_name(pattern, link)
                if link_company in list_links:
                    continue

                else:
                    list_links.append(link_company)

                print(link_company)

                await check_dreamjob(service, link_company, df_mini_pattern, df_mini_criteria, ss_id, project)
                #print(link_company)









        input('OK!')







asyncio.run(main())