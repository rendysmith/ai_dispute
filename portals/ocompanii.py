import asyncio
import random
import textwrap

import os, re
import traceback

from datetime import datetime, timedelta

from utils.gs_editor import pars_url, append_data_to_sheet_scope
from utils.ai_module import generate_and_white
from utils.user_agent import get_soup

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
    pattern = r'id=(\d+)'
    ids = re.search(pattern, url).group(1)
    return ids

async def get_top_link(link):
    try:
        soup = await get_soup(link)
        if not soup:
            return False, False

        top_url = 'https://ocompanii.net' + soup.find('a', class_='btn btn-xs btn-danger').get('href')
        print("+ top_url", top_url)
        return True, top_url

    except Exception as Ex:
        print(f"Error Top Link Ex: {Ex}")
        traceback.print_exc()
        return False, False

async def check_ocompanii(service, url, pattern, criteria, ss_id, project):
    print(url)
    ts = random.randint(5, max_sec)
    print(f'Wait {ts} sec...')
    await asyncio.sleep(ts)

    links = await pars_url(service, ss_id, project)

    status, top_link = await get_top_link(url)

    if status:
        datas = {'project': project,
                 'url': url,
                 'top_url': top_link}
        await append_data_to_sheet_scope(service, ss_id, 'unique_url', datas)

    else:
        top_link = url

    soup = await get_soup(top_link)

    if not soup:
        no_data = 'Сайт не отдал данные!'
        print('Ocompanii', no_data)
        return no_data

    blocks = soup.find_all('div', class_='col-sm-12 col-md-12')
    len_b = len(blocks)
    print(f'Len B = {len_b}')

    if len_b == 0:
        return

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

        soup = await get_soup(url_full_comm)

        if not soup:
            no_data = 'Сайт не отдал данные!'
            print('Irecommend', no_data)
            return no_data

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

async def main_oco(url):
    from utils.gs_editor import get_service
    service = await get_service()
    await check_ocompanii(service, url, 1, 1, '1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w', 1)

if "__main__" in __name__:
    url = "https://ocompanii.net/reviews/detail.php?id=1137222"
    asyncio.run(main_oco(url))

    print('*************************************************************')
    url = 'https://ocompanii.net/company/information.php?cid=764047'
    asyncio.run(main_oco(url))
    print('OK!')

