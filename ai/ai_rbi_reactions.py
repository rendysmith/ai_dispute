import asyncio
import random
import time

import os
from os.path import join, dirname, abspath

from dotenv import load_dotenv

from requests.auth import HTTPBasicAuth

import pandas as pd

from utils.gs_editor import get_service, get_table_scope, append_data_to_sheet_scope, skillbox_sheet
from utils.ai_module import get_answer_ai
from utils.constants import MODEL_GEMINI, TABLES_LIST

text = """
--------------------START COMMENT----------------------
Author: {author}
Comment: {comment}
--------------------END COMMENT----------------------
Your goal is to write consistent responses that strengthen the brand's reputation. 
It should acknowledge both positive and negative feedback, maintain a professional and courteous tone, and emphasize the brand's commitment to customer satisfaction. 
The GPT should avoid any confrontational language, ensure that responses are empathetic, and offer solutions or further assistance when needed. 
All responses must be written in Russian.
Используй названия проектов компании только в следующих написаниях:
- Струны
- Куинджи
- МИРЪ
- ARTSTUDIO M103
- Отзывы о RBI
- Ultra City
- RBI Group
- ARTSTUDIO Moskovsky
- Группа RBI
- Futurist
- Созидатели
- Дом на набережной
- Болконский
- Четыре горизонта
- Болконский

When addressing the user, always use their first name if it is in Russian (e.g., Иван Петров → Иван, здравствуйте; Маринина Ирина → Ирина, добрый день). Be aware that the first name may not always be in the first position in the pair. Do not use the name if it is a nickname or written in English.
Avoid using pronouns like 'наше', 'наш', etc.
Avoid using 'мы', 'наш'.
Do not refer to 'дома' as 'места'.
Do not abbreviate 'жилые комплексы' as ЖК.
NEVER promise the user to consider or fix something.
NEVER apologize to clients.
Adopt a style similar to the responses in the provided training set.
The GPT will receive a dataset: REVIEW, NAME, LOCATION. It must return ONLY the response.
NEVER capitalize the first letter in 'Вы', 'Ваши', 'Вас', 'Ваш' (e.g. unse only 'вы', 'ваш', 'вас', 'вами', etc.).
"""

async def ai_reaction_data_processing(service, auth, market):
    worktable_id = TABLES_LIST[market][0]
    worksheet_name = TABLES_LIST[market][1]
    worksheet_name_rec = TABLES_LIST[market][2]

    print(worktable_id, worksheet_name)
    df = await get_table_scope(service, worktable_id, worksheet_name)
    #print(list(df))
    print(df)

    for idx, row in df.iterrows():
        comment = row['Текст упоминания']
        author = row['Имя автора']
        object = row['Объект']

        prompt = text.format(author=author, comment=comment)

        result = await get_answer_ai(auth, prompt)

        data = {'Текст упоминания': comment,
                'Имя автора': author,
                'Объект': object,
                'Реакция': result}

        await append_data_to_sheet_scope(service, worktable_id, worksheet_name_rec, data)


if __name__ == '__main__':
    dotenv_path = join(dirname(dirname(__file__)), '.env')
    load_dotenv(dotenv_path)

    username = os.environ.get("HOST_USERNAME")
    password = os.environ.get("HOST_PASSWORD")
    auth = HTTPBasicAuth(username, password)
    market = 'RBI'

    service = asyncio.run(get_service())
    asyncio.run(ai_reaction_data_processing(service, auth, market))

    data = {'service_name': 'RBI', 'date': time.ctime()}
    asyncio.run(write_log_sheet(service, '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8', 'logs', data))



