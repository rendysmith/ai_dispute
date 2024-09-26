import asyncio
import os
import random

from dotenv import load_dotenv
from datetime import datetime, timedelta

from utils.gs_editor import get_service, pars_url, append_data_to_sheet_scope
from utils.ai_module import generate_and_white
from utils.user_agent import get_soup

current_date = datetime.now()

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

login_proxy = os.environ.get("LOGIN_PROXY")
pass_proxy = os.environ.get("PASS_PROXY")

async def convert_date(month):
    months = {
        'янв': 1,
        'фев': 2,
        "мар": 3,
        "апр": 4,
        "мая": 5,
        "июн": 6,
        "июл": 7,
        "авг": 8,
        "сен": 9,
        "окт": 10,
        "ноя": 11,
        "дек": 12
    }
    return months[month]

async def check_otzovik(service, link, pattern, criteria, ss_id, project):
    print(link)
    ts = random.randint(5, max_sec)
    print(f'Wait {ts} sec...')
    await asyncio.sleep(ts)

    try:
        soup = await get_soup(link)
        top_link = soup.find('h1', {"class": "product-name"})
        top_url = "https://otzovik.com" + top_link.find('a')['href'] + '?order=date_desc'
        print("top_url", top_url)

        datas = {'project': project,
                 'url': link,
                 'top_url': top_url}

        await append_data_to_sheet_scope(service, ss_id, 'unique_url', datas)

    except Exception as Ex:
        print(f"Error Ex: {Ex}")
        top_url = link

    soup = await get_soup(top_url)
    if not soup:
        return 'Сайт не отдал данные!'

    blocks = soup.find_all("div", {"itemprop": "review"})
    print(len(blocks))

    if len(blocks) == 0:
        return

    links = await pars_url(service, ss_id, project)

    for block in blocks:
        url_answer = block.find('meta', {'itemprop': "url"}).get('content')
        print(url_answer)

        if url_answer in links:
            print("Такой комментарий уже отмечен")
            continue

        date_content = block.find("div", {"class": "review-postdate"}).get('content')
        print(date_content)

        date = datetime.strptime(date_content, "%Y-%m-%dT%H:%M:%S%z")
        date = date.replace(tzinfo=None)  # offset-naive

        formatted_date = date.strftime("%d.%m.%Y")

        if (current_date - date) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней. = {date}')
            return

        author = block.find("span", {"itemprop": "name"}).text

        feedback = block.find("div", {"class": "review-body-wrap"}).text

        await generate_and_white(service=service,
                                 url_answer=url_answer,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)

# async def ya_soup():
#     url = 'https://otzovik.com/review_14926330.html?&capt4a=4291688985409980'
#     soup = await get_soup(url)
#
#     top_link = soup.find('h1', {"class": "product-name"})
#     top_url = "https://otzovik.com" + top_link.find('a')['href'] + '?order=date_desc'
#     print(top_url)
#
#     soup = await get_soup(top_url)
#
#     blocks = soup.find_all("div", {"itemprop": "review"})
#     print(len(blocks))
#
#     if len(blocks) == 0:
#         return
#
#     links = await pars_url(service, ss_id, project)
#
#     for block in blocks:
#         url_answer = block['id']
#         if url_answer in links:
#             print("Такой комментарий уже отмечен")
#             continue




async def main_otzovik():
    service = await get_service()
    url = 'https://otzovik.com/review_16566023.html'
    await check_otzovik(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", 1)


if __name__ == '__main__':
    asyncio.run(main_otzovik())