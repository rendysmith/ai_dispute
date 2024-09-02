import asyncio
import random

from datetime import datetime, timedelta

from utils.gs_editor import get_service, pars_url
from utils.ai_module import generate_and_white
from utils.user_agent import get_soup

current_date = datetime.now()

import os
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)
days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))


async def check_drive2(service, link, pattern, criteria, ss_id, project):
    print(link)
    ts = random.randint(5, max_sec)
    print(f'Wait {ts} sec...')
    await asyncio.sleep(ts)

    links = await pars_url(service, ss_id, project)
    if "#comments" not in link:
        link = link + "#comments"

    soup = await get_soup(link)
    #print(soup)

    if not soup:
        return 'Сайт не отдал данные.'

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

        feedback_html = block.find("emoji-zoom", {"data-slot": "comment.text"})
        feedback = feedback_html.text.strip()

        await generate_and_white(service=service,
                                 url_answer=url_answer,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)

    ts = random.randint(5, 15)
    await asyncio.sleep(ts)


if __name__ == '__main__':
    service = asyncio.run(get_service())
    url = 'https://www.drive2.ru/l/659074483675472672/#comments'
    asyncio.run(check_drive2(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", "Паритет"))