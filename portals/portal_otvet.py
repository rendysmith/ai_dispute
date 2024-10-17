import asyncio
import base64
import json
import random
import zlib

from datetime import datetime, timedelta, timezone

from utils.compressor import compress_string
from utils.gs_editor import get_service, pars_url, append_data_to_sheet_scope
from utils.ai_module import generate_and_white
from utils.user_agent import get_soup, get_playwright

import os
from dotenv import load_dotenv

now = datetime.now(timezone.utc)
current_date = now

month_now = now.month
year_now = now.year

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

login_proxy = os.environ.get("LOGIN_PROXY")
pass_proxy = os.environ.get("PASS_PROXY")

async def convert_date(month):
    months = {
        'янв': 1,
        'января': 1,
        'Jan': 1,
        'фев': 2,
        'февраля': 2,
        'Feb': 2,
        "мар": 3,
        "марта": 3,
        'Mar': 3,
        "апр": 4,
        "апреля": 4,
        'Apr': 4,
        "мая": 5,
        'May': 5,
        "июн": 6,
        "июня": 6,
        'Jun': 6,
        "июл": 7,
        "июля": 7,
        'Jul': 7,
        "авг": 8,
        "августа": 8,
        'Aug': 8,
        "сен": 9,
        "сентября": 9,
        'Sep': 9,
        "окт": 10,
        "октября": 10,
        'Oct': 10,
        "ноя": 11,
        "ноября": 11,
        'Nov': 11,
        "дек": 12,
        "декабря": 12,
        'Dec': 12,
    }
    return months[month]


async def check_otvet_soup(service, link, pattern, criteria, ss_id, project):
    print(link)
    soup = await get_soup(link)

    if not soup:
        return 'Сайт не отдал данные!'
    #print(soup)
    print('========================================================')
    script_tag = soup.find_all('script')
    #print(len(script_tag))
    datas = {}
    for i in script_tag:
        print(i)

        if 'Скорее всего из-за' in str(i):
            #print(f"*****************************************************\n{i}\n{type(i.text)}\n{i.text}\n---------------------------------------")
            try:
                text = i.text.replace('var QST_JSON = ', '').replace(';', '')
                #print(text)
                datas = json.loads(text)
                #print('+++++++++++++++++++++++++++++++++++++++')
                #print(type(datas))
                #input(datas)
            except:
                #input('Next...')
                return 'Данные не получены'

    if not datas:
        print(f'Datas {datas}')
        return 'Данные не получены'

    links = await pars_url(service, ss_id, project)

    if datas.get('@graph'):
        blocks = datas['@graph']
        if len(blocks) == 0:
            return
        print('--- Новые данные!!!')

    elif datas.get('result'):
        blocks = datas['result']['answers']
        if len(blocks) == 0:
            return

        for block in blocks:
            date_content = block['created_at']
            date = datetime.strptime(date_content, "%Y-%m-%dT%H:%M:%S%z")
            formatted_date = date.strftime("%d.%m.%Y")
            print(date)
            if (current_date - date) > timedelta(days=days_ago):
                print(f'--- Отзыв старше {days_ago} дней = {formatted_date}.')
                continue

            feedback = block['data']['content'][0]['text']
            print(feedback)

            author = block['author']['data']['nick']
            print(author)

            url_answer = await compress_string(feedback)

            if url_answer in links:
                print('Такой комментарий уже есть в списке')
                continue

            await generate_and_white(service=service,
                                     url_answer=url_answer,
                                     author=author,
                                     formatted_date=formatted_date,
                                     ss_id=ss_id,
                                     project=project,
                                     feedback=feedback,
                                     pattern=pattern,
                                     criteria=criteria)

async def check_otvet(service, link, pattern, criteria, ss_id, project, playwright, browser, page):
    print(link)
    #playwright, browser, page = await get_playwright(link)

    if not page:
        # await browser.close()
        # await playwright.stop()
        return 'Сайт не отдал данные'

    n = 0
    while True:
        print(n)
        if n == 10:
            await browser.close()
            await playwright.stop()
            return 'Данные сайтом не отданы'

        try:
            top_url_content = await page.query_selector('a[class="kojXG"]')
            top_url = await top_url_content.get_attribute('href')
            top_url = 'https://otvet.mail.ru' + top_url
            break

        except:
            n += 1
            await asyncio.sleep(3)

    datas = {'project': project,
             'url': link,
             'top_url': top_url}
    await append_data_to_sheet_scope(service, ss_id, 'unique_url', datas)

    await page.goto(top_url)

    await asyncio.sleep(5)
    n = 0
    while True:
        blocks_1 = await page.query_selector_all('div[class="ikwzW"]')
        len_blocks = len(blocks_1)

        if len_blocks > 0:
            break

        n += 1

        if n == 10:
            await browser.close()
            await playwright.stop()
            return 'Сайт не вернул данные.'

        await asyncio.sleep(3)

    print(len_blocks)

    if len(blocks_1) == 0:
        await browser.close()
        await playwright.stop()
        return

    blocks3 = await page.query_selector_all('div[class="de_vs"]')
    len_blocks = len(blocks3)
    print("len_blocks3", len_blocks)

    blocks4 = await page.query_selector_all('div[class="cxc3c"]')
    len_blocks = len(blocks4)
    print("len_blocks4", len_blocks)

    # await asyncio.sleep(5)
    #
    # blocks_2 = await page.query_selector_all('div[class="ezB5x"]')
    # len_blocks = len(blocks_2)
    # print(len_blocks)

    blocks = blocks_1
    links = await pars_url(service, ss_id, project)

    for block in blocks:
        date_content = await block.query_selector('a[class="Heyv4"]')
        date = await date_content.get_attribute('title')
        date_split = date.split(' ')
        print(date_split)

        day = int(date_split[0])
        month = convert_date(date_split[1])
        year = int(date_split[2])

        if month_now != month:
            continue

        if year_now != year:
            continue

        target_date = datetime(year, month, day)
        formatted_date = target_date.strftime("%d.%m.%Y")
        print(formatted_date)

        if (current_date - target_date) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней = {date}.')
            continue

        url_answer_content = await block.query_selector('a[class="Heyv4"]')
        url_answer = await url_answer_content.get_attribute('data-aid')

        if url_answer in links:
            print('Такой комментарий уже есть в списке')
            continue

        author_content = await block.query_selector('a[class="QBqbi"]')
        author = await author_content.inner_text()
        print(author)

        feedback_content = await block.query_selector('p[class="Xn2FM"]')
        feedback = await feedback_content.inner_text()
        print(feedback)

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

if __name__ == '__main__':

    service = asyncio.run(get_service())
    url = 'https://vk.com/wall-11694885_373082?reply=373184'
    url = 'https://otvet.mail.ru/answer/2042548676'
    asyncio.run(check_otvet(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", "AlphaPet"))