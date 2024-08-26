import asyncio
import random
from datetime import datetime, timedelta

from selenium.webdriver.common.by import By

from utils.gs_editor import get_service, get_table_scope, pars_url
from utils.ai_module import generate_and_white
from utils.user_agent import get_soup, get_selenium, get_playwright

import os
from dotenv import load_dotenv

now = datetime.now()
current_date = now

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

login_proxy = os.environ.get("LOGIN_PROXY")
pass_proxy = os.environ.get("PASS_PROXY")

async def convert_date(month):
    months = {
        'янв': 1,
        'Jan': 1,
        'фев': 2,
        'Feb': 2,
        "мар": 3,
        'Mar': 3,
        "апр": 4,
        'Apr': 4,
        "мая": 5,
        'May': 5,
        "июн": 6,
        'Jun': 6,
        "июл": 7,
        'Jul': 7,
        "авг": 8,
        'Aug': 8,
        "сен": 9,
        'Sep': 9,
        "окт": 10,
        'Oct': 10,
        "ноя": 11,
        'Nov': 11,
        "дек": 12,
        'Dec': 12,
    }
    return months[month]

async def check_vk_sel(service, link, pattern, criteria, ss_id, project):
    print(link)
    ts = random.randint(5, max_sec)
    print(f'Wait {ts} sec...')
    await asyncio.sleep(ts)

    links = await pars_url(service, ss_id, project)
    driver = await get_selenium(link)

    blocks = driver.find_elements(By.CSS_SELECTOR, 'div[id*="-"][class*="repl"][data-post-id*="-"]')
    len_b = len(blocks)
    print(len_b)

    if len_b == 0:
        blocks = driver.find_elements(By.CSS_SELECTOR, 'div[id*="post-"][class*="bp_post clear_fix "]')
        len_b = len(blocks)

    print(len_b)
    if len_b == 0:
        return

    for block in blocks:
        try:
            date = block.find_element(By.CSS_SELECTOR, 'span[class="rel_date"]').text.split(' ')
            print(date)

        except:
            continue

        if len(date) < 3:
            continue

        day = int(date[0])
        month = await convert_date(date[1])

        if len(date) == 4:
            year = int(datetime.now().strftime('%Y'))
        else:
            year = int(date[2])

        target_date = datetime(year, month, day)
        formatted_date = target_date.strftime("%d.%m.%Y")
        print(formatted_date)

        if (current_date - target_date) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней = {formatted_date}.')
            continue

        url_answer = block.find_element(By.CSS_SELECTOR, 'a[class="wd_lnk"]').get_attribute('href')
        if url_answer in links:
            print('Такой комментарий уже есть в списке')
            continue

        print("url_answer", url_answer)

        author = block.find_element(By.CSS_SELECTOR, 'a[class="author author_highlighted"]').text
        print("author", author)

        feedback = block.find_element(By.CSS_SELECTOR, 'div[class="wall_reply_text"]').text
        print("feedback", feedback)

        await generate_and_white(service=service,
                                 url_answer=url_answer,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)

async def blocks_vk(link):
    playwright, browser, page = await get_playwright(link)

    blocks = await page.query_selector_all('div[id*="-"][class*="repl"][data-post-id*="-"]')
    len_b = len(blocks)
    print(len_b)

    if len_b == 0:
        blocks = await page.query_selector_all('div[id*="post-"][class*="bp_post clear_fix "]')
        len_b = len(blocks)

    print(len_b)
    if len_b == 0:
        return

    return playwright, browser, blocks


async def check_vk(service, link, pattern, criteria, ss_id, project):
    print(link)
    ts = random.randint(5, max_sec)
    print(f'Wait {ts} sec...')
    await asyncio.sleep(ts)

    links = await pars_url(service, ss_id, project)

    playwright, browser, blocks = await blocks_vk(link) or (None, None, None)

    if blocks is None:
        return

    for block in blocks:
        date_content = await block.query_selector('span[class="rel_date"]')
        date = await date_content.inner_text()
        print("date =", date)

        if 'вчера' in date:
            day = now.date() - 1
            month = now.month
            year = now.year

        elif 'назад' in date:
            day = now.date()
            month = now.month
            year = now.year

        else:
            date = date.replace('\xa0', ' ')
            date_splite = date.split(' ')
            print("date_splite =", date_splite)
            day = int(date_splite[0])
            month = await convert_date(date_splite[1])

            if len(date_splite) == 4:
                year = int(datetime.now().strftime('%Y'))

            elif len(date_splite) == 5:
                year = now.year

            elif len(date_splite) == 3:
                year = int(date_splite[-1])

            else:
                year = now.year

        target_date = datetime(year, month, day)
        formatted_date = target_date.strftime("%d.%m.%Y")
        print(formatted_date)

        if (current_date - target_date) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней = {formatted_date}.')
            continue

        url_answer_content = await block.query_selector('a[class="wd_lnk"]')
        url_answer = await url_answer_content.get_attribute('href')

        if url_answer in links:
            print('Такой комментарий уже есть в списке')
            continue

        print("url_answer", url_answer)

        author_content = await block.query_selector('a[class="author author_highlighted"]')
        author = await author_content.inner_text()
        print("author", author)

        feedback_content = await block.query_selector('div[class="wall_reply_text"]')
        if not feedback_content:
            feedback_content = await block.query_selector('div[class="wall_reply_text onclick="]')

        try:
            feedback = await feedback_content.inner_text()
            print("feedback", feedback)
        except:
            print('Нет отзыва.')

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
    url = 'https://vk.com/wall-13285508_3232169'
    asyncio.run(check_vk(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", "AlphaPet"))