import asyncio
import os
import time

from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

from utils.ai_module import get_answer_ai
from utils.db_loader import read_data_from_db_filter
from utils.gs_editor import write_log_sheet, get_table_scope, get_service, append_data_to_sheet_cell
from utils.constants import TABLES_LIST

from models.mdl_tables import DatasetArticlePersons

from datetime import datetime, timedelta

now_time = datetime.now()
current_date = now_time.strftime("%d.%m.%Y")
print(current_date)

next_month = now_time + timedelta(days=30)  # Прибавляет 30 дней
worksheet_name = next_month.strftime("%b_%Y")
print(worksheet_name)

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

username = os.environ.get("HOST_USERNAME")
password = os.environ.get("HOST_PASSWORD")
auth = HTTPBasicAuth(username, password)

# text = """
# Ты блогер, {sex}, тебя зовут {fio}, тебе {age} лет и ты живешь в городе {region},
# ты {person_description}
# Твоя задача - написать статью на тему:
# {subject}
# Объем статьи должен быть {volume} знаков.
# Перед выполнением, прочитай задание еще раз.
# """

text = """
Напишите статью на тему "{subject}" в блоге, 
написанном представителем {sex} по имени {fio}, которому {age} лет и который живет в городе {region}. 
Ты {person_description}
Статья должна быть длиной примерно {volume} символов. 
Пожалуйста, внимательно изучите задание перед написанием статьи
"""

async def ai_generator_article_fun(service, auth, project):
    worktable_id = TABLES_LIST[project][0]
    #worksheet_name = TABLES_LIST[project][1]
    #worksheet_name_rec = TABLES_LIST[project][2]

    print(worktable_id, worksheet_name)
    df = await get_table_scope(service, worktable_id, worksheet_name)
    #print(list(df))
    print(df)

    for idx, row in df.iterrows():
        date = row['Date']
        #current_date = '29.08.2024'

        if current_date != date:
            print('Next day...')
            continue

        fio = row['Person']
        subject = row['Subject']

        status, result = await read_data_from_db_filter(DatasetArticlePersons, fio=fio)
        print(status)

        if status == False:
            await append_data_to_sheet_cell(service, worktable_id, worksheet_name, 'Result', idx + 2, result)

        region = result[0].region
        sex = result[0].sex
        age = result[0].age
        person_description = result[0].person_description
        volume = result[0].volume

        prompt = text.format(fio=fio, subject=subject, region=region, sex=sex, age=age, person_description=person_description, volume=volume)
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




