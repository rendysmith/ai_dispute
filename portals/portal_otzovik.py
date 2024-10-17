import asyncio
import os
import random
import traceback

from dotenv import load_dotenv
from datetime import datetime, timedelta

from utils.gs_editor import get_service, pars_url, append_data_to_sheet_scope
from utils.ai_module import generate_and_white
from utils.user_agent import get_soup, get_data_with_proxy, get_soup_anticloud, get_playwright

current_date = datetime.now()

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

login_proxy = os.environ.get("LOGIN_PROXY")
pass_proxy = os.environ.get("PASS_PROXY")

async def get_top_link(link):
    try:
        #soup = await get_soup(link)
        soup = await get_soup_anticloud(link)

        if not soup:
            return False, False

        top_link = soup.find('h1', {"class": "product-name"})
        top_url = "https://otzovik.com" + top_link.find('a')['href'] + '?order=date_desc'
        print("+ top_url", top_url)
        return True, top_url

    except TypeError as TE:
        print(f"Error Top Link TE: {TE}")
        traceback.print_exc()
        return False, link

    except Exception as Ex:
        print(f"Error Top Link Ex: {Ex}")
        traceback.print_exc()
        return False, False

async def check_otzovik_old(service, link, pattern, criteria, ss_id, project):
    print(link)

    status, top_url = await get_top_link(link)
    if not top_url:
        return 'Сайт не отдал данные!'

    print(status, top_url)

    if status:
        datas = {'project': project,
                 'url': link,
                 'top_url': top_url}

        await append_data_to_sheet_scope(service, ss_id, 'unique_url', datas)

    #soup = await get_soup(top_url)
    soup = await get_soup_anticloud(top_url)
    if not soup:
        return 'Сайт не отдал данные!'

    blocks = soup.find_all("div", {"itemprop": "review"})
    print('Len B', len(blocks))

    if len(blocks) == 0:
        return

    links = await pars_url(service, ss_id, project)

    for block in blocks:
        try:
            url_answer = block.find('meta', {'itemprop': "url"}).get('content')
        except:
            url_answer = block.find('meta', {'itemprop': "url"})

        if url_answer in links:
            print("Такой комментарий уже отмечен")
            continue

        try:
            date_content = block.find("div", {"class": "review-postdate"}).get('content')
        except:
            date_content = block.find("div", {"class": "review-postdate"})

        print("Date_content", date_content)
        date = datetime.strptime(date_content, "%Y-%m-%dT%H:%M:%S%z")
        date = date.replace(tzinfo=None)  # offset-naive

        formatted_date = date.strftime("%d.%m.%Y")

        if (current_date - date) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней. = {date}')
            return

        author = block.find("span", {"itemprop": "name"}).text
        feedback = block.find("div", {"class": "review-body-wrap"}).text

        try:
            await generate_and_white(service=service,
                                     url_answer=url_answer,
                                     author=author,
                                     formatted_date=formatted_date,
                                     ss_id=ss_id,
                                     project=project,
                                     feedback=feedback,
                                     pattern=pattern,
                                     criteria=criteria)
        except:
            print('No generate!')

async def check_otzovik(service, link, pattern, criteria, ss_id, project, playwright, browser, page):
    timeout = 10000

    await page.wait_for_selector('h1[class="product-name"]', timeout=timeout)
    top_link_content_0 = await page.query_selector('h1[class="product-name"]')
    top_link_content = await top_link_content_0.query_selector('a')
    #print('-', top_link_content)
    top_link = await top_link_content.get_attribute('href')
    #print('--', top_link)
    top_url = "https://otzovik.com" + top_link + '?order=date_desc'

    print('Top url:', top_url)

    if not top_url:
        return 'Сайт не отдал данные!'

    else:
        datas = {'project': project,
                 'url': link,
                 'top_url': top_url}

        await append_data_to_sheet_scope(service, ss_id, 'unique_url', datas)

    await page.goto(top_url)

    await page.wait_for_selector('div[itemprop="review"]', timeout=timeout)
    blocks = await page.query_selector_all('div[itemprop="review"]')

    len_b = len(blocks)
    print('Len B', len_b)

    if len_b == 0:
        await browser.close()
        await playwright.stop()
        return

    links = await pars_url(service, ss_id, project)

    for block in blocks:
        url_answer_content = await block.query_selector('meta[itemprop="url"]')
        url_answer = await url_answer_content.get_attribute('content')
        #print(url_answer)

        if url_answer in links:
            print("Такой комментарий уже отмечен")
            continue

        date_content = await block.query_selector('div[class="review-postdate"]')
        date_full = await date_content.get_attribute('content')

        #print("date_full", date_full)
        date = datetime.strptime(date_full, "%Y-%m-%dT%H:%M:%S%z")
        date = date.replace(tzinfo=None)  # offset-naive
        #print(date)

        formatted_date = date.strftime("%d.%m.%Y")
        #print(formatted_date)

        if (current_date - date) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней. = {date}')
            return

        author_content = await block.query_selector('span[itemprop="name"]')
        author = await author_content.inner_text()
        #print(author)

        feedback_content = await block.query_selector('div[class="review-body-wrap"]')
        feedback = await feedback_content.inner_text()
        #print(feedback)

        try:
            await generate_and_white(service=service,
                                     url_answer=url_answer,
                                     author=author,
                                     formatted_date=formatted_date,
                                     ss_id=ss_id,
                                     project=project,
                                     feedback=feedback,
                                     pattern=pattern,
                                     criteria=criteria)
        except:
            print('No generate!')

    await browser.close()
    await playwright.stop()







async def main_otzovik():
    url = 'https://otzovik.com/review_15821087.html'

    service = await get_service()
    playwright, browser, page = await get_playwright(url, headless=False)

    await check_otzovik(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", 1, playwright, browser, page)

if __name__ == '__main__':
    # url = 'https://otzovik.com/review_16566023.html'
    # url = 'https://otzovik.com/review_16549731.html'
    # a = asyncio.run(get_top_link(url))
    # print(a)

    asyncio.run(main_otzovik())
    print('The End!')