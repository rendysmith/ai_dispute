import asyncio
import os
import random
import re
import time

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

from models.mdl_tables import ForumRules
from utils.ai_module import get_answer_ai
from utils.central_module import wait_for_portal

from utils.db_loader import read_data_from_db_filter

from utils.gs_editor import get_service, write_log_sheet, get_table_scope, append_data_to_sheet_cell, \
    append_data_to_sheet_cells, append_data_to_sheet_scopes, append_data_to_sheet_scope

from portals.portal_otzovik import get_top_link
from utils.user_agent import get_soup

import textwrap

from datetime import datetime

# Получаем текущую дату
current_date = datetime.now()
# Преобразуем дату в формат 20.11.2024
formatted_date = current_date.strftime("%d.%m.%Y")

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

max_sec = int(os.environ.get("MAX_SEC"))

username = os.environ.get("HOST_USERNAME")
password = os.environ.get("HOST_PASSWORD")
auth = HTTPBasicAuth(username, password)

market = 'Desport'
worktable_id = '1v20Aroe8hnsKQctG-PzGPR56JfmQCntGavN9upB4cFs'
worksheet_names = ['Реагирование ОП (оф сайт/товары)', 'Реагирование ОП (гео/магазины)']
print(worktable_id, worksheet_names)

rec_worktable_id = '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8'
rec_worksheet_name = 'Desport'

prompt ="""
Ты официальный представитель компании DESPORT
ты должен предоставить профессиональный и вежливый ответ на комментарий пользователя.
Напишите ответ на следующий комментарий: 
------------НАЧАЛО КОММЕНТАРИЯ--------------
{comment}
------------КОНЕЦ КОММЕНТАРИЯ---------------
Ответ должен: 
* Начинаться со стандартного приветствия (например, "Привет" или "Добрый день").
* Завершите выступление профессиональной заключительной фразой 
(например, 
"С уважением, команда DESPORT", 
"С уважением, Ваш DESPORT", 
"Хорошего дня!" или "Желаю вам активного дня"). 

* Используйте местоимения с заглавной буквы (например, "Ты", "Вы", "Ты", "Твой") 
* Если клиента не устраивают цены, используй призыв к действию из карты реакции, в частности: 
    + Отправьте данные по электронной почте на адрес customer.support@octoblu.org 
    + Напишите в tg-чат по адресу https://t.me/desport_help_bot 
    + Ссылка на программу лояльности по адресу https://club.desport.ru/,
"""

async def cheak_desport(service):
    df_rec = await get_table_scope(service, rec_worktable_id, rec_worksheet_name)
    links = df_rec['url'].to_list()

    for worksheet_name in worksheet_names:
        df = await get_table_scope(service, worktable_id, worksheet_name)
        try:
            df = df[(df['Дата'] == formatted_date) & (df['Текст упоминания'].notnull()) & (df['Текст упоминания'] != '')]
        except Exception as Ex:
            return str(Ex)

        #print(df)
        #print(df['Текст упоминания'])

        for idx, row in df.iterrows():
            date = row['Дата']
            link = row['Ссылка на упоминание']

            if link in links:
                continue

            comment = row['Текст упоминания']

            text = prompt.format(comment=comment)
            result = await get_answer_ai(auth, text)
            print(result)

            data = {
                'date': date,
                'url': link,
                'comment': comment,
                'result': result
            }

            await append_data_to_sheet_scope(service, rec_worktable_id, rec_worksheet_name, data)

    return 'OK!'

async def main_desport():
    service = await get_service()
    status = await cheak_desport(service)

    data = {'service_name': market,
            'date': time.ctime(),
            'error': status}
    await write_log_sheet(service, '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8', 'logs', data)

if __name__ == '__main__':
    asyncio.run(main_desport())