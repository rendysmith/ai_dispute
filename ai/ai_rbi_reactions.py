import asyncio
import time

import os, json
from os.path import join, dirname, abspath

from dotenv import load_dotenv

from requests.auth import HTTPBasicAuth

from models.mdl_tables import Prompt
from utils.db_loader import read_data_from_db_filter

from utils.gs_editor import get_service, get_table_scope, append_data_to_sheet_scope, write_log_sheet
from utils.ai_module import get_answer_ai
from utils.constants import TABLES_LIST

path_dotenv = join(dirname(dirname(__file__)), '.env')
load_dotenv(path_dotenv)

username = os.environ.get("HOST_USERNAME")
password = os.environ.get("HOST_PASSWORD")
auth = HTTPBasicAuth(username, password)

path_json = join(dirname(abspath(__file__)), 'dataset_rbi.json')
print(path_json)
with open(path_json, 'r') as file:
    # Загружаем данные из файла
    patterns = json.load(file)

text = """
Ты официальный представитель компании.
Ты должен внимательно прочитать комментарий:
--------------------START COMMENT----------------------
Author: {author}
Object: {object}
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

Ты получил набор данных: ИМЯ, МЕСТОПОЛОЖЕНИЕ, ОТЗЫВ. Ты должен вернуть ТОЛЬКО ответ.
Для примера ты можешь использовать образцы текста и ответа на них:
--------------------START PATTERN----------------------
{patterns}
--------------------END PATTERN----------------------
В этом отзыве имя автора - {author}
Обращаясь к пользователю, всегда используйте его имя, если оно на русском языке (например, Иван Петров → Иван, здравствуйте; Маринина Ирина → Ирина, добрый день). 
Имейте в виду, что первое имя не всегда стоит на первом месте в паре. 
Не используйте имя, если оно является прозвищем, написано по-английски набором букв или указано как Аноним. 
Обязательно проанализируй имя автора - прежде чем использовать имя.

Избегайте использования местоимений типа «наше», «наш» и т. д.
Избегайте использования «мы», «наш».
Не сокращайте 'жилые комплексы' до ЖК.
Придерживайтесь стиля, схожего с ответами из предоставленного обучающего набора.
Уделяй внимание орфографии.
НЕ извиняйтесь перед клиентами
НЕ соглашайся с указанными минусами
НЕ обещай пользователю что-то учесть или исправить.
НЕ пиши клиенту что бы он обратил на что то внимание
НЕ используй дисклеймеры типа "Обратите внимание" и т.п. в ответе
НЕ цитируй текст пользователя.
НЕ называйте «дома» - «местами» или «место»
НИКОГДА не пишите первую букву в словах «Вы», «Ваши», «Вас», «Ваш» (например, используйте только «вы», «ваш», «вас», «вами» и т. д.).

Перед выполнением задания, прочитай его еще раз.
"""

async def ai_reaction_data_processing(service, auth, market):
    worktable_id = TABLES_LIST[market][0]
    worksheet_name = TABLES_LIST[market][1]
    worksheet_name_rec = TABLES_LIST[market][2]

    df_rec = await get_table_scope(service, worktable_id, worksheet_name_rec)
    df_comments = df_rec['Текст упоминания'].to_list()

    print(worktable_id, worksheet_name)
    df = await get_table_scope(service, worktable_id, worksheet_name)
    #print(list(df))

    df = df[df['Текст упоминания'].notna()]
    print(df)

    status, text = await read_data_from_db_filter(Prompt, project_name='rbi')
    text = text[0].prompt

    for idx, row in df.iterrows():
        comment = row['Текст упоминания']
        if comment in df_comments:
            continue

        date = row['Дата']
        author = row['Имя автора']
        object = row['Объект']

        prompt = text.format(author=author, comment=comment, patterns=patterns, object=object)

        result = await get_answer_ai(auth, prompt)

        data = {'Дата': date,
                'Текст упоминания': comment,
                'Имя автора': author,
                'Объект': object,
                'Реакция': result}

        await append_data_to_sheet_scope(service, worktable_id, worksheet_name_rec, data)


async def main_rbi():
    market = 'RBI'

    service = await get_service()
    await ai_reaction_data_processing(service, auth, market)

    data = {'service_name': 'RBI', 'date': time.ctime()}
    await write_log_sheet(service, '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8', 'logs', data)

if __name__ == '__main__':
    asyncio.run(main_rbi())

