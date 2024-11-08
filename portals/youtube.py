import asyncio
import os
import random
import time
from datetime import datetime

from dotenv import load_dotenv

from selenium.webdriver.common.by import By

from utils.ai_module import generate_and_white
from utils.compressor import compress_string
from utils.gs_editor import get_service, pars_url

from itertools import islice
from youtube_comment_downloader import *

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

current_date = datetime.now()
now_month = current_date.month
now_year = current_date.year

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

async def check_youtube(service, url, pattern, criteria, ss_id, project):
    downloader = YoutubeCommentDownloader()
    comments = downloader.get_comments_from_url(youtube_url=url, sort_by=SORT_BY_RECENT)

    links = await pars_url(service, ss_id, project)
    for comment in islice(comments, 100):
        date = comment['time_parsed']
        if time.time() - date >=  days_ago * 24 * 3600:
            print(f'--- Комментарий больше {days_ago} дней.')
            return

        formatted_date = datetime.fromtimestamp(date).strftime('%d.%m.%Y')

        url_answer = comment['cid']

        if url_answer in links:
            print('Такой комментарий уже есть в списке')
            continue

        author = comment['author'] + f'\n{url}'
        feedback = comment['text']

        await generate_and_white(service=service,
                                 url_answer=url_answer,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)

async def check_youtube_play(service, url, pattern, criteria, ss_id, project, playwright, browser, page):
    #playwright, browser, page = await get_playwright(url)
    if not page:
        # await browser.close()
        # await playwright.stop()
        return 'Сайт не отдал данные.'

    links = await pars_url(service, ss_id, project)

    await page.evaluate("document.body.style.zoom=0.5")
    await page.wait_for_timeout(5000)

    for _ in range(3):  # Прокрутка 10 раз
        await page.evaluate("window.scrollBy(0, window.innerHeight)")
        await page.wait_for_timeout(1000)  # Ожидание 1 секунды между скроллами

    blocks = await page.query_selector_all('ytd-comment-view-model[id="comment"]')
    print(len(blocks))

    if len(blocks) == 0:
        blocks = await page.query_selector_all('ytd-comment-thread-renderer[class="style-scope ytd-item-section-renderer"]')
        print(len(blocks))

    if len(blocks) == 0:
        await browser.close()
        await playwright.stop()
        return

    for block in blocks:
        try:
            date_element = await block.query_selector_all('a[class="yt-simple-endpoint style-scope ytd-comment-view-model"][href]')  # Corrected selector (should be 'meta')
            date = await date_element[-1].inner_text()
            print('date -', date)
            if any(dt in date for dt in ['год', 'year']):
                print(f'Next...({date})')
                continue

            elif any(dt in date for dt in ['дн', 'day', 'недел', 'week']):
                print(f'Next...({date})')

            else:
                continue

            date_split = date.split(' ')
            print(date_split)

            if len(date_split) == 3:
                day_int = int(date_split[0])

                if any(dt in date for dt in ['дн', 'day']):
                    sec = day_int * 24 * 3600

                elif any(dt in date for dt in ['недел', 'week']):
                    sec = day_int * 7 * 24 * 3600

            else:
                continue

        except AttributeError as AE:
            print('Error AE', AE)
            continue

        except Exception as Ex:
            print('Error YT Ex', Ex)
            continue

        feedback_text =  await block.query_selector('span[class="yt-core-attributed-string yt-core-attributed-string--white-space-pre-wrap"]')
        feedback = await feedback_text.inner_text()
        print(feedback)

        url_answer = await compress_string(feedback)

        if url_answer in links:
            print('Такой комментарий уже есть в списке')
            continue

        try:
            author_text = await block.query_selector('span[class=" style-scope ytd-comment-view-model style-scope ytd-comment-view-model"]')
            author = await author_text.inner_text()

        except AttributeError as AE:
            print(f'Error AE: {AE}, Next...')
            author_text = await block.query_selector('div[id="text-container"]')
            author = await author_text.inner_text()

        print(author)

        date = datetime.fromtimestamp(time.time() - sec)
        formatted_date = date.strftime("%d.%m.%Y")
        print(formatted_date)

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

async def check_youtube_old(service, url, pattern, criteria, ss_id, project, driver):
    # Устанавливаем масштаб страницы
    driver.execute_script("document.body.style.zoom='0.5'")
    await asyncio.sleep(5)  # Ожидание 5 секунд

    # Прокручиваем страницу 3 раза
    for _ in range(3):
        driver.execute_script("window.scrollBy(0, window.innerHeight)")
        await asyncio.sleep(5)  # Ожидание 1 секунды между прокрутками

    #blocks = await page.query_selector_all('ytd-comment-view-model[id="comment"]')
    blocks = driver.find_elements(By.CSS_SELECTOR, 'ytd-comment-view-model[id="comment"]')
    print(len(blocks))

    if len(blocks) == 0:
        #blocks = await page.query_selector_all('ytd-comment-thread-renderer[class="style-scope ytd-item-section-renderer"]')
        blocks = driver.find_elements(By.CSS_SELECTOR,
            'ytd-comment-thread-renderer[class="style-scope ytd-item-section-renderer"]')
        print(len(blocks))

    if len(blocks) == 0:
        driver.quit()
        return

    links = await pars_url(service, ss_id, project)
    for block in blocks:
        try:
            #date_element = await block.query_selector_all('a[class="yt-simple-endpoint style-scope ytd-comment-view-model"][href]')  # Corrected selector (should be 'meta')
            #date = await date_element[-1].inner_text()
            date_element = block.find_elements(By.CSS_SELECTOR,
                'a[class="yt-simple-endpoint style-scope ytd-comment-view-model"][href]')
            date = date_element[-1].text
            print('date -', date)
            if any(dt in date for dt in ['год', 'year']):
                print(f'Next...({date})')
                continue

            elif any(dt in date for dt in ['дн', 'day', 'недел', 'week']):
                print(f'Next...({date})')

            else:
                continue

            date_split = date.split(' ')
            print(date_split)

            if len(date_split) == 3:
                day_int = int(date_split[0])

                if any(dt in date for dt in ['дн', 'day']):
                    sec = day_int * 24 * 3600

                elif any(dt in date for dt in ['недел', 'week']):
                    sec = day_int * 7 * 24 * 3600

            else:
                continue

        except AttributeError as AE:
            print('Error AE', AE)
            continue

        except Exception as Ex:
            print('Error YT Ex', Ex)
            continue

        #feedback_text =  await block.query_selector('span[class="yt-core-attributed-string yt-core-attributed-string--white-space-pre-wrap"]')
        #feedback = await feedback_text.inner_text()

        feedback_text =  block.find_element(By.CSS_SELECTOR, 'span[class="yt-core-attributed-string yt-core-attributed-string--white-space-pre-wrap"]')
        feedback = feedback_text.text
        print(feedback)

        url_answer = await compress_string(feedback)

        if url_answer in links:
            print('Такой комментарий уже есть в списке')
            continue

        try:
            # author_text = await block.query_selector('span[class=" style-scope ytd-comment-view-model style-scope ytd-comment-view-model"]')
            # author = await author_text.inner_text()

            author_text = block.find_element(By.CSS_SELECTOR,
                'span[class=" style-scope ytd-comment-view-model style-scope ytd-comment-view-model"]')
            author = author_text.text

        except AttributeError as AE:
            print(f'Error AE: {AE}, Next...')
            # author_text = await block.query_selector('div[id="text-container"]')
            # author = await author_text.inner_text()

            author_text = block.find_element(By.CSS_SELECTOR, 'div[id="text-container"]')
            author = author_text.text

        print(author)

        date = datetime.fromtimestamp(time.time() - sec)
        formatted_date = date.strftime("%d.%m.%Y")
        print(formatted_date)

        await generate_and_white(service=service,
                                 url_answer=url_answer,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)

    driver.quit()

async def main_youtube():
    from utils.gs_editor import get_table_scope
    from utils.user_agent import get_selenium_proxy

    service = await get_service()
    ss_id = '1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w'
    df = await get_table_scope(service, ss_id, 'zoom')

    irec_links = df['AlphaPet'].to_list()

    for url in irec_links:
        if 'youtube' in url:
            print(url)
            await check_youtube(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", "AlphaPet")


if __name__ == '__main__':
    asyncio.run(main_youtube())
    # url = 'https://www.youtube.com/watch?v=jn7JP2iKbEs'
    # asyncio.run(check_youtube(url))


