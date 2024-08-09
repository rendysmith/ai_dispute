import asyncio
import random
import time

import os
from os.path import join, dirname, abspath

from dotenv import load_dotenv

from requests.auth import HTTPBasicAuth

import pandas as pd

from utils.gs_editor import get_service, get_table_scope, append_data_to_sheet_scope, skillbox_sheet
from utils.ai_module import get_answer_gemini
from utils.constants import MODEL_GEMINI, TABLES_LIST

async def ai_reaction_data_processing(service, auth, market):
    worktable_id = TABLES_LIST[market][0]
    worksheet_name = TABLES_LIST[market][1]
    worksheet_name_rec = TABLES_LIST[market][2]

    print(worktable_id, worksheet_name)
    df = await get_table_scope(service, worktable_id, worksheet_name)
    #print(list(df))
    print(df)

    for idx, row in df.iterrows():
        try:
            subject = df.loc[idx, 'Тематика']
        except:
            subject = market
        #mention = df.loc[rnd_idx, 'Текст упоминания']
        comment = df.loc[idx, 'Текст упоминания']

        print(subject, comment)

        # if pd.isna(mention):
        #     mention = ''

        if pd.isna(comment):
            print('pd.isna(comment)')
            continue

        elif '=COUNTA' in comment:
            print("=COUNTA' in comment:")
            continue

        word_count = len(comment.split())
        smile_count = random.randint(0, 3)

        if smile_count in [1, 3]:
            human = 'Ты мужчина/парень'
        else:
            human = 'Ты женщина/девушка'

        if smile_count > 0:
            if smile_count == 1:
                smiles = 'смайлик'
            else:
                smiles = 'смайлика'
            smile_text = f'Поставь {smile_count} {smiles}'

        else:
            smile_text = ''

        smile_place = ''

        if smile_count > 1:
            my_list = [', поставь все смайлы в разных местах.', ', поставь все смайлы в одном месте.']
            smile_place = random.choice(my_list)

        prompt = (
            f'{human}, ты отвечаешь на комментарии и как бы, просто поддерживая разговор. \n'
            f'Вот что известно:\n'
            f'Тематика: {subject}\n'
            f'Комментарий: {comment}\n'
            #f'Длинна ответа должна быть около {word_count} слов. '
            f'{smile_text}{smile_place} '
            f'Иногда можно написать с грамматическими ошибками. '
            f'Иногда можно придумать небольшую историю. '
            f'Поменьше восклицаний. '
            f'Не используй слова -Согласен- и т.п. '
            f'Ты НЕ должен вести себя как официальный представитель и т.п. '
            f'Ты должен быть максимально естественным. '
            f'Не указывай название других магазинов и маркетплейсов кроме Озона, '
            f'Вместо -тут- и т.п. указывай Озон.'
            f'Озон нельзя указывать в негативном ключе. '
            f'ОZON можно написать в разной интерпретации, например OZON, ОЗОН, Ozon, Озон, озон и т.д. НЕ использовать предлог -В- перед Озон.')

        result = await get_answer_gemini(auth, prompt, MODEL_GEMINI)
        data = {'Текст упоминания': comment,
                'result': result}
        await append_data_to_sheet_scope(service, worktable_id, worksheet_name_rec, data)
        #return comment, result, MODEL_GEMINI


if __name__ == '__main__':
    dotenv_path = join(dirname(dirname(__file__)), '.env')
    load_dotenv(dotenv_path)

    username = os.environ.get("HOST_USERNAME")
    password = os.environ.get("HOST_PASSWORD")
    auth = HTTPBasicAuth(username, password)
    market = 'OZON'

    service = asyncio.run(get_service())
    asyncio.run(ai_reaction_data_processing(service, auth, market))

    data = {'service_name': 'OZON', 'date': time.ctime()}
    asyncio.run(skillbox_sheet(service, '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8', 'logs', data))



