import asyncio
import time

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

from utils.gs_editor import get_service, get_table_scope, pars_url
from utils.ai_module import generate_and_white
from utils.user_agent import gen_ua

current_date = datetime.now()

import os
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)
days_ago = int(os.environ.get("DAYS_AGO"))


async def check_drive2(service, link, pattern, criteria, ss_id, project):
    print(link)
    links = await pars_url(service, ss_id, project)
    domen = "https://www.drive2.ru"
    headers = await gen_ua(domen)

    if "#comments" not in link:
        link = link + "#comments"

    response = requests.get(link, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    #print(soup)

    blocks = soup.find_all("div", {"data-role": "comment"})
    print(len(blocks))

    if len(blocks) == 0:
        return

    for block in blocks:
        url_answer = block['id']
        if url_answer in links:
            print("Такой комментарий уже отмечен")
            continue

        date_content = block.find("a", {"class": "c-link c-link--current u-extended-area"})['content']
        #print(type(date_content))
        #print(date_content)

        date = datetime.fromisoformat(date_content).replace(tzinfo=None)

        if (current_date - date) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней. = {date}')
            continue

        author = block.find("span", {"itemprop": "name"}).text
        author = f"{author}\n{link}"
        #print(author)

        formatted_date = date.strftime("%d.%m.%Y")
        #print(formatted_date)

        feedback = ""

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




# if __name__ == '__main__':
#     service = asyncio.run(get_service())
#     url = 'https://2gis.ru/tyumen/firm/70000001078903378/tab/reviews'
#     asyncio.run(check_2gis(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", "Паритет"))
#
#     print('Отметка о выполнении')
#     data = {'service_name': 'PRAVDA', 'date': time.ctime()}
#     asyncio.run(skillbox_sheet(service, '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8', 'logs', data))