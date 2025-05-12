import asyncio
import os
import random
from datetime import datetime, timedelta

from dotenv import load_dotenv

from selenium.webdriver.common.by import By
from sqlalchemy.sql.base import elements

from utils.central_module import wait_for_portal
from utils.gs_editor import pars_url, get_service
from utils.ai_module import generate_and_white
from utils.compressor import compress_string
from utils.user_agent import get_soup, get_playwright, get_selenium_proxy
from utils.constants import months

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

current_date = datetime.now()

timeout = 10000
async def check_rustore(service, url, pattern, criteria, ss_id, project, driver, links=False):
    # print(link)
    await wait_for_portal()

    if 'reviews' not in url:
        url = url + '/reviews'
        try:
            driver.get(url)
            print('OK!')
        except:
            driver = await get_selenium_proxy()
            driver.get(url)
            print('Error! But OK!')

    else:
        try:
            driver.get(url)
            print('OK!')

        except:
            driver = await get_selenium_proxy()
            driver.get(url)
            print('Error! But OK!')

    print('Url:', url)

    try:
        #blocks = await page.query_selector_all('li[itemprop="review"]')
        blocks = driver.find_elements(By.CSS_SELECTOR, 'li[itemprop="review"]')
        len_b = len(blocks)
        print(len_b)

    except:
        len_b = 0

    if len_b == 0:
        return

    if not links:
        links = await pars_url(service, ss_id, project)

    for block in blocks:
        #answer_develop = await block.query_selector_all('h3')
        answer_develop = block.find_elements(By.CSS_SELECTOR, 'h3')
        print(len(answer_develop))

        found_developer_answer = False
        for answer in answer_develop:
            #answer_d = await answer.inner_text()
            answer_d = answer.text
            if 'Ответ разработчика' in answer_d:
                found_developer_answer = True
                break

        if found_developer_answer:
            continue

        #date_content = await block.query_selector('p[itemprop="datePublished"]')
        #date = await date_content.inner_text()
        date = block.find_element(By.CSS_SELECTOR, 'p[itemprop="datePublished"]').text
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

        #author_content = await block.query_selector('h3[itemprop="name"]')
        #author = await author_content.inner_text()
        author = block.find_element(By.CSS_SELECTOR, 'h3[itemprop="name"]').text

        # feedback_content = await block.query_selector('p[itemprop="reviewBody"]')
        # feedback = await feedback_content.inner_text()
        feedback = block.find_element(By.CSS_SELECTOR, 'p[itemprop="reviewBody"]').text

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


async def main_rustore(url):
    service = await get_service()
    driver = await get_selenium_proxy(headless=False, proxy=False)
    await check_rustore(service, url, 1, 1, 1, 1, driver)


if __name__ == '__main__':
    url = 'https://www.rustore.ru/catalog/app/ru.sberins.insureapp.android/reviews'
    asyncio.run(main_rustore(url))
    print('The End!')
