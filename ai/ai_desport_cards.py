import asyncio
import json
import os

import time

from dotenv import load_dotenv
from numpy.core.defchararray import title

from requests.auth import HTTPBasicAuth
from datetime import datetime

from utils.ai_module import get_answer_ai
from utils.gs_editor import get_service, write_log_sheet, get_table_scope, append_data_to_sheet_cell
from utils.user_agent import get_soup



# Получаем текущую дату
current_date = datetime.now()
# Преобразуем дату в формат 20.11.2024
formatted_date = current_date.strftime("%d.%m.%Y")

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

max_sec = int(os.environ.get("MAX_SEC"))

username = os.environ.get("HOST_USERNAME")
password = os.environ.get("HOST_PASSWORD")
auth = HTTPBasicAuth(username, password)

rec_worktable_id = '1nc3dI0Tk1LfFdCiYx3nTCwy3tFrT-POES2iRXrRIl2I'
rec_worksheet_name = 'Генерация отзывов'

worktable_id = '1trdm2TPSBUXQ0e8btnR6TGRtxjO_nyqe'
worksheet_name = 'Согласование отзывов'

market = 'Desport_cards'

prompt ="""
Твоя задача написать отзыв о следующем продукте:
--------------------НАЧАЛО НАЗВАНИЕ ПРОДУКТА------------------
{subject}
--------------------КОНЕЦ НАЗВАНИЕ ПРОДУКТА------------------
--------------------НАЧАЛО ОПИСАНИЕ ПРОДУКТА-------------------
{title}
--------------------КОНЕЦ ОПИСАНИЯ ПРОДУКТА--------------------
Для примера ты можешь использовать следующие отзывы
--------------------НАЧАЛО ПРИМЕРОВ ОТЗЫВОВ--------------------
{reviews}
--------------------КОНЕЦ ПРИМЕРОВ ОТЗЫВОВ--------------------

"""

async def cheak_desport_cards(service):
    df_rec = await get_table_scope(service, rec_worktable_id, rec_worksheet_name)
    df_rec = df_rec[df_rec['отзыв_1'] != '']
    print(df_rec)

    df_reviews = await get_table_scope(service, worktable_id, worksheet_name)
    df_reviews = df_reviews[df_reviews['Отзыв'] != ''].tail(10)
    reviews = df_reviews['Отзыв'].to_list()

    for idx, row in df_rec.iterrows():
        card_url = row['Ссылка']
        count_reviews = int(row['Кол-во отзывов'])

        soup = await get_soup(card_url, proxy=False)

        subject = soup.find('title', {'data-next-head': True}).text
        print(subject)

        title_content = soup.find('script', {'id': '__NEXT_DATA__'}).text
        #print(title_content)
        title_json = json.loads(title_content)
        description = title_json['props']['pageProps']['initialState']['product']['product']['details']['description']
        print(description)

        for n in range(count_reviews):
            num = n + 1
            column_name = f'отзыв_{num}'

            text = prompt.format(subject=subject, title=title, reviews=reviews)
            result = await get_answer_ai(auth, text)

            await append_data_to_sheet_cell(service, rec_worktable_id, rec_worksheet_name, column_name, n + 2, result)





async def main_desport_cards():
    service = await get_service()
    await cheak_desport_cards(service)

    data = {'service_name': market, 'date': time.ctime()}
    await write_log_sheet(service, '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8', 'logs', data)

if __name__ == '__main__':
    asyncio.run(main_desport_cards())