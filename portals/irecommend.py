import asyncio
import random

from datetime import datetime, timedelta

from utils.gs_editor import pars_url, append_data_to_sheet_scope, get_service
from utils.ai_module import generate_and_white
from utils.user_agent import get_soup, extract_main_site, get_soup_anticloud, get_playwright
import textwrap

import os
from dotenv import load_dotenv

current_date = datetime.now()

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)
days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

async def check_irecommend_old(service, link, pattern, criteria, ss_id, project):
    #print("\n", link)
    links = await pars_url(service, ss_id, project)

    #soup = await get_soup(link)
    print('-SStart-')
    soup = await get_soup_anticloud(link)
    print('-SStop-')

    if not soup:
        no_data = 'Сайт не отдал данные!'
        print('Irecommend', no_data)
        return no_data

    try:
        denied = soup.find('h1', {'class': 'largestHeader'}).text
        if denied:
            #print(denied)
            return denied
    except:
        print('Страница доступна')

    domen = await extract_main_site(link)

    try:
        top_block = soup.find("div", {"class": "headerWithMenu margin30"})
        print(f'Получение главной темы на основании комментов.')
        top_url = domen + top_block.find("a")['href'] + "?new=1"
        #print(top_url)

    except AttributeError as AE:
        print('!!!(irecommend) Возможно сработала защита Cloudflore...')
        #checkbox = soup.find('input', {'type': 'checkbox'})
        return AE

    except Exception as Ex:
        return Ex

    datas = {'project': project,
             'url': link,
             'top_url': top_url}

    await append_data_to_sheet_scope(service, ss_id, 'unique_url', datas)

    #soup = await get_soup(top_url)
    soup = await get_soup_anticloud(top_url)

    try:
        blocks = soup.find_all("div", {"data-photos-count": '0', "data-type": "1"})
        len_b = len(blocks)
        print(f'Leb blocks = {len_b}')
        if len_b == 0:
            return

    except:
        return 'Возможно сработала защита Cloudflore'

    for block in blocks:
        url_n = block.find("a", class_='reviewTextSnippet')['href']
        url_answer = domen + url_n
        if url_answer in links:
            print('Отзыв уже есть в таблице')
            continue

        try:
            date = block.find("div", {"class": "created"}).text
            target_date = datetime.strptime(date, "%d.%m.%Y")

        except:
            date_1 = block.find("div", {"class": "created"})
            date = date_1.find("span", {"class": "date-created"}).text
            target_date = datetime.strptime(date, "%d.%m.%Y")

        if (current_date - target_date) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней = {date}.')
            continue

        author = block.find("div", class_="authorName").text

        title = block.find("div", {"class": "reviewTitle"}).text
        title_txt = block.find("span", {"class": "reviewTeaserText"}).text

        feedback = f"""
        {title}
        {title_txt}
        """
        feedback = textwrap.dedent(feedback)
        #print(feedback)

        formatted_date = date

        #await generate_and_white(service, url_answer, author, formatted_date, prompt)
        await generate_and_white(service=service,
                                 url_answer=url_answer,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)

async def check_irecommend(service, link, pattern, criteria, ss_id, project, playwright, browser, page):
    timeout = 10000

    # Создание новой вкладки
    new_page = await browser.new_page()

    # Теперь вы можете работать с new_page
    await new_page.goto(link)


    input('1')

    try:
        checkbox = page.locator('input[type="checkbox"]')
        await checkbox.wait_for(state='visible', timeout=timeout)
        await checkbox.click()

        # # Ждем появления чекбокса
        # await page.wait_for_selector('input[type="checkbox"]', timeout=timeout)
        # input('Next..')
        # # Если чекбокс появился, кликаем по нему
        # await page.click('input[type="checkbox"]')

    except TimeoutError:
        # Если чекбокс не появился в течение времени таймаута, продолжаем выполнение
        print("Чекбокс не найден, продолжаем выполнение")

    input('Wait...')

    await browser.close()
    await playwright.stop()






async def main(url):
    service = await get_service()

    playwright, browser, page = await get_playwright(url, headless=False)
    await check_irecommend(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", 1, playwright, browser, page)

if "__main__" in __name__:
    url = "https://irecommend.ru/content/dlya-bystrogo-rosta-i-razvitiya"
    #top_url = "https://irecommend.ru/content/cordiant-snow-cross-2"
    #print(top_url)

    asyncio.run(main(url))



