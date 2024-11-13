import asyncio
import os
import time

import pandas as pd
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

from utils.ai_module import get_answer_ai
from utils.db_loader import read_data_from_db_filter
from utils.gs_editor import write_log_sheet, get_table_scope, get_service, append_data_to_sheet_cell
from utils.constants import TABLES_LIST
from utils.central_module import get_articles

from models.mdl_tables import DatasetArticlePersons

from datetime import datetime, timedelta

pd.set_option('display.max_columns', None)

now_time = datetime.now()
current_date = now_time.strftime("%d.%m.%Y")
print(current_date)

next_month = now_time + timedelta(days=30)  # Прибавляет 30 дней

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

username = os.environ.get("HOST_USERNAME")
password = os.environ.get("HOST_PASSWORD")
auth = HTTPBasicAuth(username, password)

text_fun = """
Ты копирайтер и автор статей.
ты {gender} по имени {fio}, которому {age} лет и который живет в городе {region}. 
Ты {person_description}
Напишите статью на тему "{subject}" в блоге:
Статья должна быть длиной примерно 5000 символов символов. 
Что запрещено:
Азартные игры, лотереи, стимулирующие мероприятия: Запрещена любая реклама и пропаганда участия.
Дублированный контент: Повторная публикация материалов.
Заимствованный контент: Публикация чужого контента без указания авторства.
Запрещённые товары и услуги: Наркотики, оружие, торговля людьми и т.д.
Искусственное завышение показателей: Накрутка просмотров, дочитываний, подписчиков.
Кликбейт: Заголовки и карточки, обманывающие ожидания пользователей.
Ложная информация и фейки: Публикация недостоверных фактов.
Незаконная информация: Призывы к противоправным действиям, нарушению прав, размещение ссылок на нелегальный контент.
Неприятное изображение на карточке: Фотографии, вызывающие отвращение (насекомые, туши животных, и т.д.)
Оскорбления и нападки: Грубые высказывания, травля, запугивание.
Откровенный контент: Материалы эротического характера.
Происшествия и трагедии: Спекуляция на чужом горе.
Сниженная лексика: Обилие нецензурной лексики и жаргонизмов.
Спам: Распространение нерелевантной информации.
Товары и услуги, вредящие здоровью: Реклама и пропаганда табака, алкоголя, вейпов.
Шокирующий контент: Изображения насилия, трупов, травм.
Язык вражды и пропаганда насилия: Разжигание ненависти, дискриминация, призывы к насилию.
Что разрешено с ограничениями:
Медицина и фармацевтика: Допустимы информационные материалы с опорой на доказательную медицину, без призывов к самолечению и рекламы конкретных препаратов.
Важно помнить:
Указывайте авторство при использовании чужих материалов.
Не используйте кликбейт и шокирующий контент на карточках публикаций.
Будьте вежливы и уважайте других пользователей.
Пожалуйста, внимательно изучите задание перед написанием статьи
"""

async def ai_generator_article_fun(service, auth, project):
    worktable_id = TABLES_LIST[project][0]
    worksheet_name = next_month.strftime("%b_%Y")
    print(worksheet_name)

    worksheet_name_2 = now_time.strftime("%b_%Y")
    print(worksheet_name_2)

    #worksheet_name = TABLES_LIST[project][1]
    #worksheet_name_rec = TABLES_LIST[project][2]

    df_pers = await get_table_scope(service, worktable_id, 'persons')

    try:
        df = await get_table_scope(service, worktable_id, worksheet_name)

    except:
        worksheet_name = worksheet_name_2
        df = await get_table_scope(service, worktable_id, worksheet_name)

    print(worksheet_name)
    print(df)

    for idx, row in df.iterrows():
        date = row['Date']

        if current_date != date:
            print('Next day...')
            continue

        result = row['Result']
        if pd.notna(result):
            print(f'Next {idx}...')
            continue

        fio = row['Person']

        idx_pers = df_pers.index[df_pers['fio'] == fio].tolist()

        region = df_pers.loc[idx_pers, 'region']
        gender = df_pers.loc[idx_pers, 'gender']
        age = df_pers.loc[idx_pers, 'age']
        person_description = df_pers.loc[idx_pers, 'person_description']

        topic_url = row['Topic']
        articles = await get_articles(topic_url)

        top_number = int(row['Top_number'])

        subject = articles.loc[top_number - 1, 0]

        prompt = text_fun.format(fio=fio, subject=subject, region=region, gender=gender, age=age, person_description=person_description)
        result = await get_answer_ai(auth, prompt)
        await append_data_to_sheet_cell(service, worktable_id, worksheet_name, 'Result', idx + 2, result)

async def main_article():
    project = 'Article_fun'
    service = await get_service()
    await ai_generator_article_fun(service, auth, project)

    data = {'service_name': project, 'date': time.ctime()}
    await write_log_sheet(service, '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8', 'logs', data)


if __name__ == '__main__':
    asyncio.run(main_article())




