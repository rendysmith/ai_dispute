import asyncio
import random

from datetime import datetime, timedelta, timezone

from utils.compressor import compress_string
from utils.gs_editor import pars_url, get_service, append_data_to_sheet_scope
from utils.ai_module import generate_and_white
from utils.user_agent import get_soup

import os
from dotenv import load_dotenv

current_date = datetime.now(timezone.utc)

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

async def convert_date(month):
    months = {
        'января': 1,
        'февраля': 2,
        "марта": 3,
        "апреля": 4,
        "мая": 5,
        "июня": 6,
        "июля": 7,
        "августа": 8,
        "сентября": 9,
        "октября": 10,
        "ноября": 11,
        "декабря": 12
    }
    return months[month]

async def get_id_obj(url):
    url_split = url.split('/')
    print("url_split", url_split)
    #city_company = url_split[3]

    for idx, v in enumerate(url_split):
        if v == 'firm':
            id_obj = url_split[idx+1]
            break

        elif v == 'orgs':
            id_obj = url_split[idx + 1]
            break

    return id_obj

async def send_top_url(service, ss_id, project, url):
    id_obj = await get_id_obj(url)
    top_url = f'https://2gis.ru/firm/{id_obj}'
    print(top_url)

    datas = {'project': project,
             'url': url,
             'top_url': top_url}

    await append_data_to_sheet_scope(service, ss_id, 'unique_url', datas)

async def check_2gis(service, url, pattern, criteria, ss_id, project):
    links = await pars_url(service, ss_id, project)
    ts = random.randint(5, max_sec)
    print(f'Wait {ts} sec...')
    await asyncio.sleep(ts)

    id_org = await get_id_obj(url)
    url = f'https://public-api.reviews.2gis.com/2.0/branches/{id_org}/reviews?limit=50&is_advertiser=true&fields=meta.providers,meta.branch_rating,meta.branch_reviews_count,meta.total_count,reviews.hiding_reason,reviews.is_verified&without_my_first_review=false&rated=true&sort_by=friends&key=b0209295-ae15-48b2-acb2-58309b333c37&locale=ru_RU'

    r_json = await get_soup(url, only_text=False)

    blocks = r_json['reviews']

    for block in blocks:
        date_content = block['date_created']
        date = datetime.strptime(date_content, "%Y-%m-%dT%H:%M:%S.%f%z")

        if (current_date - date) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней. = {date}')
            continue

        url_answer = block['id']
        if url_answer in links:
            print('Такой комментарий уже есть в списке')
            continue

        official_answer = block['official_answer']
        if not official_answer:
            print("Уже есть ответ компании.")
            continue

        formatted_date = date.strftime("%d.%m.%Y")
        print(formatted_date)

        feedback = block['text']

        author = block['user']['name']
        author = f"{author}\n{url}"

        await generate_and_white(service=service,
                                 url_answer=url_answer,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)





async def check_2gis_old(service, url, pattern, criteria, ss_id, project, playwright, browser, page):
    #playwright, browser, page = await get_playwright(url)

    ts = random.randint(5, max_sec)
    print(f'Wait {ts} sec...')
    await asyncio.sleep(ts)

    if not page:
        # await browser.close()
        # await playwright.stop()
        return "Сайт не вернул данные"

    if 'go' in url:
        final_url = page.url
        print("final_url:", final_url)
        await send_top_url(service, ss_id, project, final_url)

    else:
        await send_top_url(service, ss_id, project, url)

    links = await pars_url(service, ss_id, project)

    blocks = await page.query_selector_all('div[class="_11gvyqv"]')
    print('Len =', len(blocks))

    if len(blocks) == 0:
        await browser.close()
        await playwright.stop()
        return

    for block in blocks:
        try:
            date_content = await block.query_selector('div[class="_4mwq3d"]')
            date = await date_content.inner_text()
            date_split = date.split(', ')[0].split(' ')
            date_split = [dt.replace(',', '') for dt in date_split]
            #print(date_split)

        except AttributeError as AE:
            print(f'AE: {AE}')
            date_content = await block.query_selector('div[class="_139ll30"]')
            date = await date_content.inner_text()
            date_split = date.split(' ')
            date_split = [dt.replace(',', '') for dt in date_split]
            #print(date_split)
            print(f'AE: OK!')

        day = int(date_split[0])
        month = await convert_date(date_split[1])
        year = int(date_split[2])

        target_date = datetime(year, month, day)
        formatted_date = target_date.strftime("%d.%m.%Y")
        #print(formatted_date)

        if (current_date - target_date) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней = {date}.')
            continue

        try:
            answer_content = block.query_selector('div[class="_sgs1pz"]')
            answer = answer_content.inner_text()
            print('Уже есть ответ на комментарий')
            continue

        except:
            pass

        author_content = await block.query_selector('span[class="_16s5yj36"]')
        author = await author_content.inner_text()
        author = author.strip()
        #print('\n', author)

        feedback_content = await block.query_selector('div[class="_49x36f"]')
        feedback = await feedback_content.inner_text()
        #print(feedback)

        url_answer = await compress_string(feedback)

        if url_answer in links:
            print('Такой комментарий уже есть в списке')
            continue

        author = f"{author}\n{url}"

        await generate_and_white(service=service,
                                 url_answer=url_answer,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)

    await browser.close()
    await playwright.stop()

async def main_2gis(url):
    service = await get_service()
    #playwright, browser, page = await get_playwright(url)
    await check_2gis_new(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", 1)

if __name__ == '__main__':
    url = 'https://2gis.ru/tyumen/firm/70000001078903378/65.581594%2C57.166876/tab/reviews'
    #url = 'https://go.2gis.com/dgzo35'
    url = 'https://2gis.ru/ufa/search/%D0%BD%D0%BE%D0%B2%D0%B8%D0%BA%D0%BE%D0%BC%D0%B1%D0%B0%D0%BD%D0%BA%20%D1%83%D1%84%D0%B0/firm/70000001064543956/56.135469%2C54.787878/tab/reviews?m=56.039914%2C54.760852%2F12.5'
    url = 'https://2gis.ru/voronezh/firm/70000001044544643/tab/reviews'

    #url = 'https://2gis.ru/tyumen/firm/70000001083501286/tab/reviews'
    asyncio.run(main_2gis(url))
