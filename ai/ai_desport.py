import asyncio
import os
import random
import re
import time

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

from models.mdl_tables import ForumRules, Prompt
from utils.ai_module import get_answer_ai
from utils.central_module import wait_for_portal

from utils.db_loader import read_data_from_db_filter

from utils.gs_editor import get_service, write_log_sheet, get_table_scope, append_data_to_sheet_cell, \
    append_data_to_sheet_cells, append_data_to_sheet_scopes, append_data_to_sheet_scope, get_all_sheet_names

from portals.portal_otzovik import get_top_link
from utils.user_agent import get_soup

import textwrap

from datetime import datetime

# Получаем текущую дату
current_date = datetime.now()
# Преобразуем дату в формат 20.11.2024
formatted_date = current_date.strftime("%d.%m.%Y")
print(formatted_date)

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

max_sec = int(os.environ.get("MAX_SEC"))

username = os.environ.get("HOST_USERNAME")
password = os.environ.get("HOST_PASSWORD")
auth = HTTPBasicAuth(username, password)

market = 'Desport'
worktable_id = '1v20Aroe8hnsKQctG-PzGPR56JfmQCntGavN9upB4cFs'
worksheet_names = ['Реагирование ОП (гео/магазины)', 'Реагирование ОП (оф сайт/товары)']
print(worktable_id, worksheet_names)

rec_worktable_id = '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8'
rec_worksheet_name = 'Desport'

async def get_prompt():
    status, text = await read_data_from_db_filter(Prompt, project_name='desport')
    if status:
        prompt = text[0].prompt
        return prompt

    else:
        return status

async def cheak_desport(service):
    tabs = await get_all_sheet_names(service, worktable_id)
    print(tabs)

    for wn in worksheet_names:
        if wn not in tabs:
            return f'ERROR: No *{wn}* in desport sheets'

    prompt = await get_prompt()
    if not prompt:
        return 'Error prompt'

    df_rec = await get_table_scope(service, rec_worktable_id, rec_worksheet_name)
    links = df_rec['url'].to_list()

    for worksheet_name in worksheet_names:
        print(f'---------------{worksheet_name}------------------')
        df = await get_table_scope(service, worktable_id, worksheet_name)

        columns = df.columns
        #print(columns)

        date_name = 'Дата'
        text_name = 'Текст упоминания'
        link_name = 'Ссылка на упоминание'

        for names in [date_name, text_name, link_name]:
            if names not in columns:
                return f'ERROR: No head *{names}* in *{worksheet_name}*'

        try:
            df = df[(df[date_name] == formatted_date) & (df[text_name].notnull()) & (df[text_name] != '')]

        except Exception as Ex:
            return print(f'Error: {Ex}')

        #print(df['Текст упоминания'])

        for idx, row in df.iterrows():
            date = row[date_name]
            link = row[link_name]

            if link in links:
                continue

            comment = row[text_name]

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