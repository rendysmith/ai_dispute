import asyncio
import os
import time

from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

from models.mdl_tables import ForumRules
from utils.ai_module import get_answer_ai

from utils.constants import TABLES_LIST
from utils.db_loader import read_data_from_db_filter

from utils.gs_editor import get_service, write_log_sheet, get_table_scope, append_data_to_sheet_cell

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
Если комментарий нарушает какое-либо правило, укажите, какое правило он нарушает. 
В противном случае укажите, что он не нарушает никаких правил
Так же тебе нужно оценить вероятность удаление отзыва основываясь на указанных правилах выше, 
где (можно 80-100% | сомнительно 50-79% | нельзя >49%).
"""

async def cheak_vkusvill(service, market):
    worktable_id = TABLES_LIST[market][0]
    worksheet_name = TABLES_LIST[market][1]

    print(worktable_id, worksheet_name)

    df = await get_table_scope(service, worktable_id, worksheet_name)
    add_column = 'Текст для поддержки'
    df = df[df[add_column].isnull()]

    print(df)

    for idx, row in df.iterrows():
        #link = row['Url']
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

        response = await append_data_to_sheet_cell(service, worktable_id, worksheet_name, add_column, idx + 2, str(result))
        print(response)
        #input()














async def main_vkusvill():
    market = 'Vkusvill'

    service = await get_service()
    await cheak_vkusvill(service, market)

    data = {'service_name': market, 'date': time.ctime()}
    await write_log_sheet(service, '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8', 'logs', data)

if __name__ == '__main__':
    asyncio.run(main_vkusvill())


