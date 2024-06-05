import asyncio
import random
import time

import pandas as pd

from utils.gs_editor import (
    get_table_scope,
    get_service,
    append_data_to_sheet_scope,
    append_data_to_sheet_cell,
    append_data_to_sheet_cells,
    read_table_id,
    skillbox_sheet)

from utils.ai_module import get_answer_gemini, get_answer_gpt

#df = await read_table_id("144vfSzkSRikNif--93raEJgSmWL8OnArEho02AlA2Q8", "Портреты АВ")



async def ai_reaction_data_processing(service, row, engine):
    comment = row['Негатив']
    print(comment)

    #word_count = len(comment.split())

    df_pers = await read_table_id(service, "1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8", "Портреты АВ")
    persons = df_pers['persons'].to_list()
    person = random.choice(persons)

    df_prom = await read_table_id(service, "1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8", "prompts")
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

    if 'gemini' in engine:
        result = await get_answer_gemini(prompt, engine)
    elif 'gpt' in engine:
        result = await get_answer_gpt(prompt, engine)

    return result
#
# if __name__ == '__main__':
#     values = ["""На ПМЭФ не хватает эскортниц
# Агентства, предоставляющие вип-девушек, заявляют, что в этом году на эскортниц небывалый ажиотаж. Всех разобрали ещё за две недели до форума.
# Цены взлетели до небес: от 700 тысяч до миллиона в сутки за “сопровождающую”.""",
#               "Хуситы на ПМЭФ",
#               """В Петербурге возник дефицит секс-работниц из-за предстоящего ПМЭФ-2024
# В специализированных агентствах сообщили, что цены на девушек взлетели до 700 тысяч рублей за обычную и до миллиона за VIP-девушку.
# Как дела в офисе?"""]
#     for value in values:
#         row = {"Негатив": value}
#         res = asyncio.run(ai_reaction_data_processing(row, "gemini-pro"))
#         print("ОТВЕТ 1:\n", res)
#
# input()

async def main_react_old():
    worktable_id = '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8'
    worksheet_name = 'PMEF'

    df = await read_table_id(worktable_id, worksheet_name)
    df = df[(df['Негатив'].notna()) & ((df['Вариант 1'].isna()) | (df['Вариант 2'].isna()))]
    print(df)

    col_gemini = 'Вариант 1'
    col_gpt = 'Вариант 2'

    for idx, row in df.iterrows():
        res_gemini = row[col_gemini]
        res_gpt = row[col_gpt]

        if pd.notna(res_gemini) and pd.notna(res_gpt):
            print(f'В строке {idx} есть оба результата')
            continue

        row_number = idx + 2

        if pd.isna(res_gemini):
            async def main_react():

                result_gemini = await ai_reaction_data_processing(service, row, 'gemini-1.5-pro')
            await append_data_to_sheet_cell(worktable_id, worksheet_name, col_gemini, row_number, result_gemini)
            print(f'{row_number} {col_gemini} - OK!')
            await asyncio.sleep(2)

        if pd.isna(res_gpt):
            result_gpt = await ai_reaction_data_processing(service, row, 'gpt-3.5-turbo')
            await append_data_to_sheet_cell(worktable_id, worksheet_name, col_gpt, row_number, result_gpt)
            print(f'{row_number} {col_gpt} - OK!')
            await asyncio.sleep(2)

        await asyncio.sleep(5)


async def main_react(service):

    worktable_id = '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8'
    worksheet_name = 'PMEF'

    df = await read_table_id(service, worktable_id, worksheet_name)
    df = df[(df['Негатив'].notna()) & ((df['Вариант 1'].isna()) | (df['Вариант 2'].isna()))]
    print(df)

    col_gemini = 'Вариант 1'
    col_gpt = 'Вариант 2'

    columns = [col_gemini, col_gpt]

    for idx, row in df.iterrows():
        res_gemini = row[col_gemini]
        res_gpt = row[col_gpt]

        if pd.notna(res_gemini) and pd.notna(res_gpt):
            print(f'В строке {idx} есть оба результата')
            continue

        row_number = idx + 2

        #result_gemini = await ai_reaction_data_processing(row, 'gemini-1.5-pro')
        #print(f'Gemini OK!\n{result_gemini}')
        #result_gpt = await ai_reaction_data_processing(row, 'gpt-3.5-turbo')
        #print(f'GPT OK!\n{result_gpt}')

        # result_gemini_task = ai_reaction_data_processing(row, 'gemini-1.5-pro')
        # result_gpt_task = ai_reaction_data_processing(row, 'gpt-3.5-turbo')
        # await asyncio.gather(result_gemini_task, result_gpt_task)

        task1 = asyncio.create_task(ai_reaction_data_processing(service, row, 'gemini-1.5-pro'))
        task2 = asyncio.create_task(ai_reaction_data_processing(service, row, 'gpt-3.5-turbo'))

        result_gemini = await task1
        result_gpt = await task2

        print(f'Gemini OK!')
        print(f'GPT OK!')

        results = [result_gemini, result_gpt]
        await append_data_to_sheet_cells(service, worktable_id, worksheet_name, columns, row_number, results)
        #print(f'{row_number} - OK!')
        await asyncio.sleep(10)


if __name__ == '__main__':
    service = asyncio.run(get_service())
    asyncio.run(main_react(service))
    data = {'service_name': 'PMEF', 'date': time.ctime()}
    asyncio.run(skillbox_sheet(service, '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8', 'logs', data))








