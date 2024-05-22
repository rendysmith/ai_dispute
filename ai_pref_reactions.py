import asyncio
import random
import time

import pandas as pd

from utils.gs_editor import get_table_scope, append_data_to_sheet_scope, append_data_to_sheet_cell, read_table_id
from utils.ai_module import get_answer_gemini, get_answer_gpt

async def ai_reaction_data_processing(row, engine):
    comment = row['Негатив']

    word_count = len(comment.split())

    humans = ['Ты мужчина,', 'Ты женщина,']
    human = random.choice(humans)

    years = random.randint(25, 45)
    years_old = f'тебе {years} лет,'

    prompt = f"""
{human}, {years_old}, ты среднестатистический россиянин, 
ты читаешь комментарий,
Комментарий: {comment}
Твоя главная задача:
- закрыть негатив отзыва
- не использовать слишком восхищенные фразы
"""

    if 'gemini' in engine:
        result = await get_answer_gemini(prompt, engine)
    elif 'gpt' in engine:
        result = await get_answer_gpt(prompt, engine)

    #result, engine = await ai_generator_react(market=market, comment=comment, subject=subject)
    return result

async def main():
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

asyncio.run(main())



