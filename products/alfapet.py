import os
import time
from datetime import datetime, timedelta
from pprint import pprint

from dotenv import load_dotenv

import asyncio
from urllib.parse import urlparse

from utils.ai_module import generate_and_white
from utils.gs_editor import read_table_id, get_service
from utils.constants import TABLES_LIST

from portals.portal_vk import blocks_vk

ss_id = TABLES_LIST['zoom']
now = datetime.now()

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)
days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

async def get_domen(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    if domain != '':
        return domain

    else:
        return

async def vk_parser(service, url_answer):
    comments = await blocks_vk(url_answer)
    await asyncio.sleep(5)

    if not comments:
        return

    for comment in comments:

        pprint(comment)

        date = comment['date']
        date_ts = datetime.fromtimestamp(date)

        print(type(now))
        print(type(date_ts))
        print(type(days_ago))

        formatted_date = date_ts.strftime("%d.%m.%Y")
        if (now - date_ts) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней = {formatted_date}.')
            continue

        author = comment['author_name']
        feedback = comment['text']

        await generate_and_white(service=service,
                                 url_answer=url_answer,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project="AlphaPet",
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)





async def main_alfa():
    service = await get_service()

    df = await read_table_id(service, ss_id, 'zoom')

    df_mini = df[["Проект", "AlphaPet"]]
    print(df_mini)

    # for ind, row in df_mini.iterrows():
    #     if "Пример реакции" in row['Проект']:
    #         print(row['AlphaPet'])
    #
    # input()



    df_mini_pattern = [row["AlphaPet"] for ind, row in df_mini.iterrows() if "Пример реакции" in row['Проект']]
    print(df_mini_pattern)

    df_mini_criteria = [row["AlphaPet"] for ind, row in df_mini.iterrows() if "Особые критерии" in row['Проект']]
    input(df_mini_criteria)
    input()

    links_alfa = df['AlphaPet'].tolist()
    print(links_alfa)

    domens = {}

    for _url in links_alfa:
        if "google.com" in _url:
            continue

        domen = await get_domen(_url)
        if domen:
            domens[domen] = []

    print(domens)

    for url_ in links_alfa:
        for k in domens.keys():
            if k in url_:
                domens[k].append(url_)
                break

    print(domens)

    for key, value in domens.items():
        print(f"------------------{key}--------------------")
        for url in value:
            if "vk.com" in url:
                await vk_parser(service, url)











if "__main__" in __name__:
    asyncio.run(main_alfa())