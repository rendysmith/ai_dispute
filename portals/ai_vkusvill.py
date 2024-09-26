import asyncio
import os
import time

from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

from models.mdl_tables import ForumRules
from utils.ai_module import get_answer_ai

from utils.constants import TABLES_LIST
from utils.db_loader import read_data_from_db_filter

from utils.gs_editor import get_service, write_log_sheet, get_table_scope, append_data_to_sheet_cell, \
    append_data_to_sheet_cells

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

username = os.environ.get("HOST_USERNAME")
password = os.environ.get("HOST_PASSWORD")
auth = HTTPBasicAuth(username, password)

text = """
Ты модератор сайта {source},
Твоя задача:
ты должен внимательно прочитать комментарий
----------------Начало комментария ---------------
{comment}
----------------Конец комментария ----------------
ты должен на основании ниже приведенных правил дать заключение, нарушает ли данное сообщение какое либо правило, если нарушает указать какой именно пункт
---------------Начало правил-----------------
ЗАПРЕЩЕНО:
{rule}
---------------Конец правил------------------
"""

text = """
Ты модератор сайта {source},
Посмотри следующий комментарий: 
{comment} 
Определите, нарушает ли он какое-либо из следующих правил: 
{rule} 
Если комментарий нарушает какое-либо правило, укажите, какое именно правило он нарушает в формате: 
'*новая строка* *Порядковый номер строки, например*: Пункт правила и его текст и обязательно текст отзыва или его часть которое нарушает правило'.  
В противном случае укажите, что он не нарушает никаких правил.
Так же тебе нужно оценить вероятность удаление отзыва основываясь на указанных правилах выше, 
где (можно 80-100% | сомнительно 50-79% | нельзя >49%).
Ты должен выдать результат в формате списка [], 
где первый элемент будет процент удаления, 
второй - резюме о нарушениях правил площадки если таковы будут
Оба элемента должны быть в формате string, т.е. в кавычках. 
Перед выполнением прочитай задание еще раз.
"""

# text = """
# Оцените комментарий '{comment}' на соответствие правилам сайта:
# '{rule}'.
# Определите, нарушает ли он какое-либо из этих правил.
# Если нарушает, укажите, какое правило он нарушает, и процитируйте соответствующий текст или часть комментария, которая нарушает правило.
# Оформите результат в виде списка с двумя элементами:
# * процент удаления комментария, классифицированный как «возможно» (80-100 %), «сомнительно» (50-79 %) или «невозможно» (>49 %), в кавычках.
# * Краткое описание нарушений, включая правило и соответствующий текст комментария, если таковой имеется.
# Выведите результат в формате, который можно использовать напрямую, с каждым элементом, заключенным в двойные кавычки."""

async def cheak_vkusvill(service, market):
    worktable_id = TABLES_LIST[market][0]
    worksheet_name = TABLES_LIST[market][1]

    print(worktable_id, worksheet_name)

    df = await get_table_scope(service, worktable_id, worksheet_name)
    add_column = 'Текст для поддержки'
    df = df[df[add_column].isnull()]

    print(df)

    for idx, row in df.iterrows():
        brand = 'ВкусВилл'
        link = row['Url']
        comment = row['Текст']
        source = row['Источник']

        project = source.split('.')[0]

        status, rules_db = await read_data_from_db_filter(ForumRules, forum_name=project)
        if status:
            if len(rules_db) > 0:
                rule = rules_db[0].forum_rule

            else:
                continue

        else:
            continue

        prompt = text.format(source=source, comment=comment, rule=rule)
        result = await get_answer_ai(auth, prompt)
        print(result)

        try:
            result = eval(result)
            result[1] = f"Здравствуйте, Я представляю интересы компании {brand} и хочу обратиться с просьбой удалить отзыв {link}. Отзыв содержит нарушение:\n" + result[1]

            columns = ['Вероятность удаления', 'Текст для поддержки']
            await append_data_to_sheet_cells(service, worktable_id, worksheet_name, columns, idx + 2, result)

        except SyntaxError as SE:
            print(f'ERROR: {SE}')





async def main_vkusvill():
    market = 'Vkusvill'

    service = await get_service()
    await cheak_vkusvill(service, market)

    data = {'service_name': market, 'date': time.ctime()}
    await write_log_sheet(service, '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8', 'logs', data)


async def grade_analysis():



if __name__ == '__main__':
    #asyncio.run(main_vkusvill())


