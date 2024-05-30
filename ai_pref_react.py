import asyncio
import random
import time

import pandas as pd

from utils.gs_editor import get_table_scope, append_data_to_sheet_scope, append_data_to_sheet_cell, read_table_id, skillbox_sheet
from utils.ai_module import get_answer_gemini, get_answer_gpt

#df = await read_table_id("144vfSzkSRikNif--93raEJgSmWL8OnArEho02AlA2Q8", "Портреты АВ")

async def ai_reaction_data_processing(row, engine):
    comment = row['Негатив']

    word_count = len(comment.split())

    df_pers = await read_table_id("1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8", "Портреты АВ")
    persons = df_pers['persons'].to_list()
    person = random.choice(persons)

    df_prom = await read_table_id("1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8", "prompts")
    # Поиск индекса элемента в колонке project_name
    index = df_prom[df_prom['project_name'] == 'pref'].index[0]

    # Получение элемента из колонки prompt_1 по найденному индексу
    prompt_1 = df_prom.at[index, 'prompt_1']

    prompt = f"""
Роль: {person},
Тема: Общение на форуме ПМЭФ (Петербургский международный экономический форум).
Комментарий: {comment}
{prompt_1}
"""
    print(prompt)
#Тип и длина текста: Ответное сообщение, не более 3-х предложений.
# Аудитория: Участники форума ПМЭФ, вероятно, профессионалы и заинтересованные в экономических и бизнес-темах.
# Задача:
# Ответить на комментарий,
# закрыть негатив,
# сделать общение более позитивным,
# без использования слишком восхищенных фраз,
# не использовать официальный и строгий стиль общения

    if 'gemini' in engine:
        result = await get_answer_gemini(prompt, engine)
    elif 'gpt' in engine:
        result = await get_answer_gpt(prompt, engine)

    #result, engine = await ai_generator_react(market=market, comment=comment, subject=subject)
    return result
#
row = {"Негатив": "С 5 по 8 июня в Санкт-Петербурге проходит Петербургский Международный Экономический Форум."}
res = asyncio.run(ai_reaction_data_processing(row, "gemini-pro"))
print("ОТВЕТ:\n", res)
input()

async def main_react():
    worktable_id = '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8'
    worksheet_name = 'PMEF'

    df = await read_table_id(worktable_id, worksheet_name)
    print(df)

    col_gemini = 'Вариант 1'
    col_gpt = 'Вариант 2'

    for idx, row in df.iterrows():
        res_gemini = row[col_gemini]
        res_gpt = row[col_gpt]

        if pd.notna(res_gemini) and pd.notna(res_gpt):
            print('В строке есть оба результата')
            continue

        row_number = idx + 2

        if pd.isna(res_gemini):
            result_gemini = await ai_reaction_data_processing(row, 'gemini-pro')
            await append_data_to_sheet_cell(worktable_id, worksheet_name, col_gemini, row_number, result_gemini)
            print(f'{row_number} {col_gemini} - OK!')

        if pd.isna(res_gpt):
            result_gpt = await ai_reaction_data_processing(row, 'gpt-3.5-turbo')
            await append_data_to_sheet_cell(worktable_id, worksheet_name, col_gpt, row_number, result_gpt)
            print(f'{row_number} {col_gpt} - OK!')

        time.sleep(5)

if __name__ == '__main__':
    asyncio.run(main_react())
    data = {'service_name': 'PMEF', 'date': time.ctime()}
    asyncio.run(skillbox_sheet('1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8', 'logs', data))








