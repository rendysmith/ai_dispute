import asyncio
import os
import random
import re
import time
from xml.sax.handler import feature_external_ges

import numpy as np
import pandas as pd
from asyncpg.compat import wait_for
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

from models.mdl_tables import ForumRules
from utils.ai_module import get_answer_ai
from utils.central_module import wait_for_portal

from utils.constants import TABLES_LIST
from utils.db_loader import read_data_from_db_filter

from utils.gs_editor import get_service, write_log_sheet, get_table_scope, append_data_to_sheet_cell, \
    append_data_to_sheet_cells

from portals.portal_otzovik import get_top_link
from utils.user_agent import get_soup

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

max_sec = int(os.environ.get("MAX_SEC"))

username = os.environ.get("HOST_USERNAME")
password = os.environ.get("HOST_PASSWORD")
auth = HTTPBasicAuth(username, password)

text = """
Ты модератор сайта {source},
Твоя задача:
ты должен внимательно прочитать комментарий
----------------Начало комментария ---------------
{comment}
----------------Конец комментария ----------------
ты должен на основании ниже приведенных правил дать заключение, нарушает ли данное сообщение какое либо правило, если нарушает указать какой именно пункт
---------------Начало правил-----------------
ЗАПРЕЩЕНО:
{rule}
---------------Конец правил------------------
"""

text = """
Ты модератор сайта {source},
Посмотри следующий комментарий: 
{comment} 
Определите, нарушает ли он какое-либо из следующих правил: 
{rule} 
Если комментарий нарушает какое-либо правило, укажите, какое именно правило он нарушает в формате: 
'*новая строка* *Порядковый номер строки, например*: Пункт правила и его текст и обязательно текст отзыва или его часть которое нарушает правило'.  
В противном случае укажите, что он не нарушает никаких правил.
Так же тебе нужно оценить вероятность удаление отзыва основываясь на указанных правилах выше, 
где (можно 80-100% | сомнительно 50-79% | нельзя >49%).
Ты должен выдать результат в формате списка [], 
где первый элемент будет процент удаления, 
второй - резюме о нарушениях правил площадки если таковы будут
Оба элемента должны быть в формате string, т.е. в кавычках. 
Перед выполнением прочитай задание еще раз.
"""

# text = """
# Оцените комментарий '{comment}' на соответствие правилам сайта:
# '{rule}'.
# Определите, нарушает ли он какое-либо из этих правил.
# Если нарушает, укажите, какое правило он нарушает, и процитируйте соответствующий текст или часть комментария, которая нарушает правило.
# Оформите результат в виде списка с двумя элементами:
# * процент удаления комментария, классифицированный как «возможно» (80-100 %), «сомнительно» (50-79 %) или «невозможно» (>49 %), в кавычках.
# * Краткое описание нарушений, включая правило и соответствующий текст комментария, если таковой имеется.
# Выведите результат в формате, который можно использовать напрямую, с каждым элементом, заключенным в двойные кавычки."""

market = 'Vkusvill'
worktable_id = TABLES_LIST[market][0]
worksheet_name = TABLES_LIST[market][1]
print(worktable_id, worksheet_name)

async def extract_link_from_line(url):
    # Шаблон для поиска ссылки от https: до .html
    pattern = r"https:.*?\.html"
    # Поиск ссылки в строке
    match = re.search(pattern, url)
    if match:
        return match.group(0)
    return None

async def cheak_vkusvill(service):
    df = await get_table_scope(service, worktable_id, worksheet_name)
    add_column = 'Текст для поддержки'
    df = df[df[add_column].isnull()]

    print(df)

    for idx, row in df.iterrows():
        brand = 'ВкусВилл'
        link = row['Url']
        comment = row['Текст']
        source = row['Источник']

        project = source.split('.')[0]

        status, rules_db = await read_data_from_db_filter(ForumRules, forum_name=project)
        if status:
            if len(rules_db) > 0:
                rule = rules_db[0].forum_rule

            else:
                continue

        else:
            continue

        prompt = text.format(source=source, comment=comment, rule=rule)
        result = await get_answer_ai(auth, prompt)
        print(result)

        try:
            result = eval(result)
            result[1] = f"Здравствуйте, Я представляю интересы компании {brand} и хочу обратиться с просьбой удалить отзыв {link}. Отзыв содержит нарушение:\n" + result[1]

            columns = ['Вероятность удаления', 'Текст для поддержки']
            await append_data_to_sheet_cells(service, worktable_id, worksheet_name, columns, idx + 2, result)

        except SyntaxError as SE:
            print(f'ERROR: {SE}')





async def main_vkusvill():
    service = await get_service()
    await cheak_vkusvill(service)

    data = {'service_name': market, 'date': time.ctime()}
    await write_log_sheet(service, '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8', 'logs', data)


async def grade_analysis():
    service = await get_service()
    df = await get_table_scope(service, worktable_id, worksheet_name)
    not_null = 'Текст'
    is_null = 'Общий Url'
    df = df[(df[not_null].notnull() & df[is_null].isnull())]

    columns = ['Общий Url', 'Ссылка Url']

    print(df)
    for idx, row in df.iterrows():
        portal = row['Источник']
        link = row['Url']
        print(link)

        if portal == 'otzovik.com':
            feeback_link = await extract_link_from_line(link)

            await wait_for_portal()
            status, top_link = await get_top_link(link) #Получаем топовую ссылку
            if not status:
                result = ['Ошибка, проверить страницу на актульность.', feeback_link]
                await append_data_to_sheet_cells(service, worktable_id, worksheet_name, columns, idx + 2, result)
                await asyncio.sleep(5)
                continue

            print("top_link",top_link)

            soup = await get_soup(top_link)
            if not soup:
                await asyncio.sleep(5)
                continue

            error_page = soup.find('h1')
            for er in error_page:
                if 'Ошибка' in er.text:

                    result = ['Ошибка, проверить страницу на актульность.', feeback_link]
                    await append_data_to_sheet_cells(service, worktable_id, worksheet_name, columns, idx + 2, result)
                    await asyncio.sleep(5)
                    continue


            overall_grade = soup.find('div', class_='rating-score-2 big').text.strip()
            number_grades = soup.find('span', class_='votes').text.strip()

            columns = ['Общий Url', 'Ссылка Url', 'Кол-во отзывов', 'Оценка компании до удаления']
            result = [top_link, feeback_link, number_grades, overall_grade]
            await append_data_to_sheet_cells(service, worktable_id, worksheet_name, columns, idx + 2, result)

            await asyncio.sleep(5)

        elif portal == 'nerab.ru':
            pass




async def total_grade_analysis(service):
    df = await get_table_scope(service, worktable_id, worksheet_name)

    data_rows = []
    for idx, row in df.iterrows():
        company_link = row['Общий Url']
        feedback_counts = row['Кол-во отзывов']

        if pd.isna(feedback_counts):
            # print('Next...')
            continue

        df_mini = df[df['Общий Url'] == company_link]
        df_mini = df_mini.drop_duplicates(subset=["Ссылка Url"])
        df_mini["Оценка"] = pd.to_numeric(df_mini["Оценка"], errors='coerce')  # Преобразуем в числа

        counts_feedback = float(df_mini['Кол-во отзывов'].iloc[-1])
        company_rating = float(df_mini['Оценка компании до удаления'].iloc[-1])

        total_sum = counts_feedback * company_rating
        total_negative_sum = df_mini["Оценка"].sum()
        total_negative_count = df_mini["Оценка"].count()

        finish_sum = total_sum - total_negative_sum
        finish_counts = counts_feedback - total_negative_count
        finish_rating = round(finish_sum / finish_counts, 1)

        for idx_mini, row_mini in df_mini.iterrows():
            rating = row_mini['Оценка компании после удаления']

            if pd.notnull(rating):
                #print('Next...')
                continue

            if idx_mini not in data_rows:
                await append_data_to_sheet_cell(service, worktable_id, worksheet_name,'Оценка компании после удаления', idx_mini + 2, finish_rating)
                data_rows.append(idx_mini)





async def main_grade():
    service = await get_service()
    #asyncio.run(main_vkusvill())

    #asyncio.run(grade_analysis())
    await total_grade_analysis(service)





if __name__ == '__main__':
    asyncio.run(main_grade())
