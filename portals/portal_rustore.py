import asyncio
import os
import random
from datetime import datetime, timedelta

from dotenv import load_dotenv

from utils.gs_editor import pars_url
from utils.ai_module import generate_and_white
from utils.compressor import compress_string
from utils.user_agent import get_soup, get_playwright
from utils.constants import months

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

current_date = datetime.now()

timeout = 10000
async def check_rustore(service, url, pattern, criteria, ss_id, project, playwright, browser, page):
    # print(link)
    links = await pars_url(service, ss_id, project)

    if 'reviews' not in url:
        url = url + '/reviews'
        await page.goto(url)

    print(url)

    await page.wait_for_selector('li[itemprop="review"]', timeout=timeout)
    blocks = await page.query_selector_all('li[itemprop="review"]')
    len_b = len(blocks)
    print(len_b)

    if len_b == 0:
        await browser.close()
        await playwright.stop()
        return

    for block in blocks:
        answer_develop = await block.query_selector_all('h3')
        print(len(answer_develop))

        found_developer_answer = False
        for answer in answer_develop:
            answer_d = await answer.inner_text()
            if 'Ответ разработчика' in answer_d:
                found_developer_answer = True
                break

        if found_developer_answer:
            continue

        date_content = await block.query_selector('p[itemprop="datePublished"]')
        date = await date_content.inner_text()
        date_split = date.split(' ')
        print(date_split)

        day = int(date_split[0])
        month = int(months[date_split[1]])
        year = int(date_split[2])

        target_date = datetime(year, month, day)
        formatted_date = target_date.strftime("%d.%m.%Y")

        if (current_date - target_date) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней = {date}.')
            continue

        author_content = await block.query_selector('h3[itemprop="name"]')
        author = await author_content.inner_text()

        feedback_content = await block.query_selector('p[itemprop="reviewBody"]')
        feedback = await feedback_content.inner_text()

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

    await browser.close()
    await playwright.stop()









    # soup = await get_soup(url)
    # print(soup)
    # print(soup.title)
    #
    # #blocks = soup


async def main_rustore(url):
    playwright, browser, page = await get_playwright(url)
    await check_rustore(1, url, 1, 1, 1, 1, playwright, browser, page)


if __name__ == '__main__':
    url = 'https://www.rustore.ru/catalog/app/ru.sberins.insureapp.android/reviews'
    asyncio.run(main_rustore(url))
    print('The End!')
