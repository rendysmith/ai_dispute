import asyncio
import random
import time

import os, json
from os.path import join, dirname, abspath

from dotenv import load_dotenv

from requests.auth import HTTPBasicAuth

import pandas as pd

from utils.gs_editor import get_service, get_table_scope, append_data_to_sheet_scope, write_log_sheet
from utils.ai_module import get_answer_ai
from utils.constants import MODEL_GEMINI, TABLES_LIST

text = """
--------------------START COMMENT----------------------
Author: {author}
Comment: {comment}
--------------------END COMMENT----------------------
Ваша цель - написать последовательные ответы, которые укрепят репутацию бренда. 
В них следует признавать как положительные, так и отрицательные отзывы, поддерживать профессиональный и вежливый тон, 
а также подчеркивать стремление бренда удовлетворить потребности клиентов. 
Ты должен избегать любых конфронтационных высказываний, обеспечивать сопереживание в ответах и предлагать решения или дальнейшую помощь, когда это необходимо. 
Все ответы должны быть написаны на русском языке.

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

Ты получишь набор данных: ОТЗЫВ, ИМЯ, МЕСТОПОЛОЖЕНИЕ. Ты должен вернуть ТОЛЬКО ответ.
Для примера ты можешь использовать образцы текста и ответа на них:
--------------------START PATTERN----------------------
{patterns}
--------------------END PATTERN----------------------
Обращаясь к пользователю, всегда используйте его имя, если оно на русском языке (например, Иван Петров → Иван, здравствуйте; Маринина Ирина → Ирина, добрый день). 
Имейте в виду, что первое имя не всегда стоит на первом месте в паре. Не используйте имя, если оно является прозвищем или написано по-английски.
Избегайте использования местоимений типа «наше», «наш» и т. д.
Избегайте использования «мы», «наш».
Не называйте «дома» - «местами».
Не сокращайте 'жилые комплексы' до ЖК.
Придерживайтесь стиля, схожего с ответами из предоставленного обучающего набора.
НЕ используй дисклеймеры типа "Обратите внимание" и т.п. в ответе
НИКОГДА не извиняйтесь перед клиентами.
НИКОГДА не пишите первую букву в словах «Вы», «Ваши», «Вас», «Ваш» (например, используйте только «вы», «ваш», «вас», «вами» и т. д.).
НИКОГДА не обещайте пользователю что-то учесть или исправить.
"""

with open('dataset_rbi.json', 'r') as file:
    # Загружаем данные из файла
    patterns = json.load(file)

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

        prompt = text.format(author=author, comment=comment, patterns=patterns)

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



