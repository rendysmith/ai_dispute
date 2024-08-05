import asyncio
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time

from utils.gs_editor import get_service, get_table_scope, pars_url
from utils.ai_module import generate_and_white
from utils.user_agent import gen_ua
import textwrap

current_date = datetime.now()

import os
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)
days_ago = int(os.environ.get("DAYS_AGO"))


async def check_irecommend(service, link, pattern, criteria, ss_id, project):
    links = await pars_url(service, ss_id, project)
    print(links)

    domen = "https://irecommend.ru"
    headers = await gen_ua(domen)

    response = requests.get(link, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    #print(soup)

    top_block = soup.find("div", {"class": "headerWithMenu margin30"})
    print(top_block)

    top_url = domen + top_block.find("a")['href'] + "?new=1"
    print(top_url)

    response = requests.get(top_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    blocks = soup.find_all("div", {"data-photos-count": '0', "data-type": "1"})
    print(len(blocks))

    for block in blocks:
        url_n = block.find("a", class_='reviewTextSnippet')['href']
        url_answer = domen + url_n
        if url_answer in links:
            print('Отзыв уже есть в таблице')
            continue

        date = block.find("div", {"class": "created"}).text
        print(date)

        target_date = datetime.strptime(date, "%d.%m.%Y")

        if (current_date - target_date) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней = {date}.')
            continue

        author = block.find("div", class_="authorName").text

        title = block.find("div", {"class": "reviewTitle"}).text
        title_txt = block.find("span", {"class": "reviewTeaserText"}).text

        feedback = f"""
        {title}
        {title_txt}
        """
        feedback = textwrap.dedent(feedback)
        print(feedback)

        formatted_date = date

        #await generate_and_white(service, url_answer, author, formatted_date, prompt)
        await generate_and_white(service=service,
                                 url_answer=url_answer,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)

    time.sleep(5)


# async def main(url):
#     service = await get_service()
#     await check_irecommend(service, url, 1,1,'1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w','Кордиант')
#
# if "__main__" in __name__:
#     url = "https://irecommend.ru/content/vtoroi-sezon-polet-normalnyi-2"
#     top_url = "https://irecommend.ru/content/cordiant-snow-cross-2"
#     #print(top_url)
#
#     asyncio.run(main(url))



