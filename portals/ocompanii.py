import asyncio
import random
import textwrap

import requests
import os, re

from bs4 import BeautifulSoup

from datetime import datetime, timedelta

from utils.gs_editor import pars_url
from utils.ai_module import generate_and_white
from utils.user_agent import gen_ua

current_date = datetime.now()

abspath = os.path.dirname(os.path.abspath(__file__))
cor_path = os.path.abspath(os.curdir)

import os
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)
days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

async def extract_ids(url):
    print(url)
    pattern = r'id=(\d+)'
    ids = re.search(pattern, url).group(1)
    return ids

async def check_ocompanii(service, url, pattern, criteria, ss_id, project):
    ts = random.randint(5, max_sec)
    print(f'Wait {ts} sec...')
    await asyncio.sleep(ts)

    print(url)
    links = await pars_url(service, ss_id, project)
    domen = "https://ocompanii.net"
    headers = await gen_ua(domen)

    #url = 'https://ocompanii.net/company/information.php?cid=764047'
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    blocks = soup.find_all('div', class_='col-sm-12 col-md-12')
    print(len(blocks))

    for block in blocks:
        #print('**************************************')
        date_meta = block.find('meta', {'itemprop': 'datePublished'})
        #print(date_meta)

        try:
            date_content = date_meta['content']
            print(date_content)
        except:
            continue

        date = datetime.strptime(date_content, "%Y-%m-%d %H:%M:%S")
        #print("date", date)
        formatted_date = date.strftime("%d.%m.%Y")

        if (current_date - date) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней. = {date}')
            continue

        url_comment = block.find('a', {'itemprop': 'url'})
        url_answer = "https://ocompanii.net" + url_comment['href']
        #print(url_answer)

        if url_answer in links:
            print(f'{url_answer}\nНа этот отзыв уже есть реакция!\n')
            continue

        author = block.find('meta', {'itemprop': 'name'}).text.strip()
        #print(author)

        id_ = await extract_ids(url_answer)

        url_full_comm = f'https://ocompanii.net/reviews/load_detail.php?id={id_}'

        response = requests.get(url_full_comm, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser').text
        #print(type(soup))
        #print(soup)

        p_m = soup.split('###')

        plus = p_m[-2]
        minus = p_m[-1]

        feedback = f"""
        Положительные стороны
        {plus}
        Отрицательные стороны
        {minus}
        """
        feedback = textwrap.dedent(feedback)

        await generate_and_white(service=service,
                                 url_answer=url_answer,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)

