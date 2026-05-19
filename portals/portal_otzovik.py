import asyncio
import os
import random
import sys
import time
from datetime import datetime, timedelta

import pandas as pd
import requests

from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from twocaptcha import TwoCaptcha, AsyncTwoCaptcha
from playwright_captcha import TwoCaptchaSolver, CaptchaType, FrameworkType

from utils.ai_module import generate_and_white
from utils.central_module import wait_for_portal, proxy_status, get_hpo
from utils.constants import TABLES_LIST, empty_data, months
from utils.gs_editor import get_service, pars_url, get_table_scope, write_log_sheet, append_data_to_sheet_scope, \
    append_data_to_sheet_cell, read_table_id, append_data_to_sheet_scopes
from utils.user_agent import get_selenium_proxy, get_playwright
from utils.proxy_bridge import set_windows_proxy

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

corn_folder = os.path.dirname(os.path.dirname(__file__))

current_date = datetime.now()

record_date = current_date.strftime("%d.%m.%Y")

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)
days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))
captcha_key = os.environ.get("CAPTCHA_KEY")
print(captcha_key)

ss_id = TABLES_LIST['zoom']

headless, proxy_on, only_text = asyncio.run(get_hpo())
headless = False

print(f"Headless = {headless}, proxy = {proxy_on}")

recorded = 0

# print(f'- local_ip Otzovik: {local_ip} {headless} {proxy_on}')

async def date_convert(date_str):
    parts = date_str.split()
    date = 'Не определено'
    if len(parts) == 3:
        day = parts[0].zfill(2)
        month_value = months.get(parts[1].lower(), '00')
        month = str(month_value).zfill(2)
        year = parts[2]
        date = f"{day}.{month}.{year}"

    return date

async def transform_reviews_to_dict(reviews_list):
    """
    Преобразует список словарей в словарь с массивами значений.

    Пример:
    Вход: [{'a': 1, 'b': 2}, {'a': 3, 'b': 4}]
    Выход: {'a': [1, 3], 'b': [2, 4]}
    """
    if not reviews_list:
        return {}

    # Получаем заголовки из первого словаря
    # (предполагаем, что все словари имеют одинаковую структуру)
    columns = list(reviews_list[0].keys())

    # Создаем словарь с пустыми списками
    result = {col: [] for col in columns}

    # Заполняем значения
    for item in reviews_list:
        for col in columns:
            result[col].append(item.get(col, ''))

    return result

async def solve_captcha(page):
    captcha_client = AsyncTwoCaptcha(captcha_key)

    async with TwoCaptchaSolver(framework=FrameworkType.PLAYWRIGHT,
                                page=page,
                                async_two_captcha_client=captcha_client
                                ) as solver:
        await solver.solve_captcha(
            captcha_container=page,
            captcha_type=CaptchaType.RECAPTCHA_V2 # Или другой тип, если Отзовик обновится
        )

async def sent_captcha(file_link):
    print('--- Send captcha...')
    solver = TwoCaptcha(apiKey=captcha_key, )

    n = 0
    while n < 10:
        result = solver.normal(file_link)
        #print(result)
        if result.get('code'):
            #print(result['code'])
            return result['code']

        await asyncio.sleep(1)
        n += 1
        print(f'nC = {n}')

    return None

async def normalize_otzovik_date(date_str):
    """
    Преобразует строковую дату Otzovik в формат dd.mm.YYYY.
    Учитывает текущую дату как 14.05.2026 (на основе предоставленных данных).
    """
    if not date_str or not isinstance(date_str, str):
        return date_str

    # Текущая дата для расчетов (из вашего контекста)


    today = datetime.now()  # или datetime.today()

    date_str = date_str.lower().strip()

    # 1. Обработка ключевых слов
    if date_str == 'сегодня':
        return today.strftime('%d.%m.%Y')
    if date_str == 'вчера':
        return (today - timedelta(days=1)).strftime('%d.%m.%Y')

    # 2. Обработка дней недели
    weekdays = {
        'понедельник': 0, 'вторник': 1, 'среда': 2,
        'четверг': 3, 'пятница': 4, 'суббота': 5, 'воскресенье': 6
    }

    if date_str in weekdays:
        target_weekday = weekdays[date_str]
        current_weekday = today.weekday()
        # Вычисляем разницу (идем назад до ближайшего дня недели)
        days_ago = (current_weekday - target_weekday) % 7
        if days_ago == 0:  # Если сегодня четверг и в логе "четверг", значит это было 7 дней назад
            days_ago = 7
        res_date = today - timedelta(days=days_ago)
        return res_date.strftime('%d.%m.%Y')

    # 3. Обработка форматов "15 мар" или "16 фев 2018"
    # months = {
    #     'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4, 'май': 5, 'июн': 6,
    #     'июл': 7, 'авг': 8, 'сен': 9, 'окт': 10, 'ноя': 11, 'дек': 12
    # }

    parts = date_str.split()
    if len(parts) >= 2:
        try:
            day = int(parts[0])
            # Берем первые 3 буквы месяца для сопоставления со словарем
            month_name = parts[1][:3]
            month = months.get(month_name, 1)

            if len(parts) == 3:
                # Формат: "16 фев 2018"
                year = int(parts[2])
            else:
                # Формат: "15 мар" (текущий год)
                year = today.year

            return f"{day:02d}.{month:02d}.{year}"
        except (ValueError, IndexError):
            return date_str

    return date_str

async def check_captcha(page):
    while True:
        try:
            captcha_count = await page.locator('img[id="captcha-img"]').count()
            if captcha_count > 0:
                print('Captcha found, wait 5 sec...')
                await asyncio.sleep(5)

            else:
                print('--- No captcha')
                return

        except:
            print('--- No captcha')
            return

async def get_top_link(driver):
    try:
        top_link_content = driver.find_element(By.CSS_SELECTOR, 'h1.product-name')
        top_link = top_link_content.find_element(By.CSS_SELECTOR, 'a')
        #print(top_link.get_attribute('href'))
        return top_link.get_attribute('href')

    except:
        print('--- func No top link')
        return

    #         await page.wait_for_selector('h1[class="product-name"]', timeout=timeout)
    #         top_link_content_0 = await page.query_selector('h1[class="product-name"]')
    #         top_link_content = await top_link_content_0.query_selector('a')
    #         top_link = await top_link_content.get_attribute('href')

async def captcha_check(driver):
    print('>>> Capcha? <<<')
    url = 'https://2captcha.com/'
    r = requests.get(url)
    status_code = r.status_code
    if status_code != 200:
        print(f'Capcha {url} = {status_code}')
        return None

    print("-- Refresh")
    driver.refresh()
    await wait_for_portal()

    n = 0
    while n < 10:
        try:
            try:
                tbody = driver.find_element(By.CSS_SELECTOR, 'input[type="text"]')
                #print("--- tbody\n", tbody)

            except:
                print('--- No tbody')
                #print(driver.page_source)

            capcha = driver.find_elements(By.CSS_SELECTOR, 'img[src]')

            len_c = len(capcha)
            print(f'-- Len_c = {len_c}')

            if len_c != 1:
                print('++ No captcha!')
                return driver

            number_file = int(time.time())
            print('- 1', number_file)
            temp_path = os.path.join(corn_folder, 'temp')
            if not os.path.exists(temp_path):
                os.makedirs(temp_path)
                print(f"+++ Папка <{temp_path}> создана.")
            else:
                print(f"+++ Папка <{temp_path}> уже существует.")

            file_link = os.path.join(temp_path, f'captcha_image_{number_file}.png')
            print('- 2', file_link)

            capcha[0].screenshot(file_link)
            print(f"-- Скриншот капчи сохранен по адресу {file_link}")

            capcha_text = await sent_captcha(file_link)
            print(capcha_text)

            input_captcha = driver.find_element(By.CSS_SELECTOR, 'input[type="text"]')
            input_captcha.send_keys(capcha_text)

            await asyncio.sleep(3)
            input_captcha.send_keys(Keys.RETURN)

            if os.path.exists(file_link):
                os.remove(file_link)
                print("-- Файл удален")
            else:
                print("-- Файл не найден")
            break

        except Exception as Ex:
            n += 1
            print(f'Error captcha: {Ex}')
            await wait_for_portal()

    return driver

async def get_feedback(page, url):
    await page.goto(url)
    await check_captcha(page)
    text = await page.locator('div.item-right').inner_text()
    await asyncio.sleep(2)
    return text

async def blocks_otzovik(page, page2, links, min_rating, max_rating):
    blocks = await page.locator('div[class="item status4 mshow0"]').all()

    datas = await empty_data()

    for block in blocks:
        rating = int(await block.locator('div[class="rating-score tooltip-right"]').inner_text())

        if min_rating <= rating <= max_rating:
            review_url_content = await block.locator('a.review-btn.review-read-link').get_attribute('href')
            review_url = f"https://otzovik.com{review_url_content}"

            if review_url in links:
                continue

            text = await get_feedback(page2, review_url)

            date_content = await block.locator('div.review-postdate').get_attribute('content')
            date = datetime.strptime(date_content, "%Y-%m-%dT%H:%M:%S%z")
            date = date.replace(tzinfo=None)  # offset-naive
            formatted_date = date.strftime("%d.%m.%Y")

            author = await block.locator('span[itemprop="name"]').inner_text()

            datas['Дата'].append(formatted_date)
            datas['Текст'].append(text)
            datas['Url'].append(review_url)
            datas['Автор'].append(author)
            datas['Оценка'].append(rating)

    return datas

async def full_blocks_otzovik(service, ss_id, project, page, page_2):

    results = []

    # 1. Сбор всех карточек отзывов на текущей странице
    # Используем селектор для контейнера каждого отзыва
    review_cards = await page.query_selector_all('div.item.status4.mshow0')
    print(f'Len cards = {len(review_cards)}')

    for card in review_cards:
        # --- Сбор данных с основной страницы (page) ---

        # Дата отзыва
        date_el = await card.query_selector('.review-postdate span')
        date_str = await date_el.inner_text() if date_el else None
        review_date = await date_convert(date_str)

        # Оценка
        rating_el = await card.query_selector('.rating-score span')
        rating = await rating_el.inner_text() if rating_el else None

        # Текст отзыва (тизер)
        text_el = await card.query_selector('.review-teaser')
        review_text = await text_el.inner_text() if text_el else ""

        # Ссылка на отзыв
        link_el = await card.query_selector('a.review-title')
        review_link = ""
        if link_el:
            review_link = "https://otzovik.com" + await link_el.get_attribute('href')

        if review_link in lists:
            continue

        # Автор и ссылка на автора
        author_el = await card.query_selector('a.user-login')
        author_name = ""
        author_link = ""
        if author_el:
            author_name = (await author_el.inner_text()).strip()
            author_link = "https://otzovik.com" + await author_el.get_attribute('href')

        # Проверка на ответ Официального Представителя (ОП)
        # В списке отзывов ОП обычно отображается в блоке комментария с пометкой
        op_response_el = await card.query_selector('.review-comment-official')  # Стандартный класс для ответа ОП
        has_op_response = "Да" if op_response_el else "Нет"

        # Дата ответа ОП (если есть в тизере, иначе ищем внутри - но по ТЗ собираем с карточки)
        op_response_date = None
        if op_response_el:
            op_date_el = await op_response_el.query_selector('.comment-postdate')
            if op_date_el:
                op_response_date = await op_date_el.inner_text()

        # --- Сбор данных со страницы автора (page_2) ---
        reg_date = None
        author_reviews_count = 0
        author_comments_count = 0

        if author_link:
            try:
                # Переходим на страницу автора во втором окне
                await page_2.goto(author_link)
                await check_captcha(page_2)
                #await solve_captcha(page=page_2)

                # Дата регистрации
                reg_date_el = await page_2.query_selector('.regdate span:last-child')
                if reg_date_el:
                    reg_date_str = await reg_date_el.inner_text()
                    reg_date = await normalize_otzovik_date(reg_date_str)

                # Кол-во отзывов
                rev_count_el = await page_2.query_selector('.row.reviews .val span')
                if rev_count_el:
                    author_reviews_count = await rev_count_el.inner_text()

                # Кол-во комментариев
                comm_count_el = await page_2.query_selector('.row.comments .val')
                if comm_count_el:
                    author_comments_count = (await comm_count_el.inner_text()).strip()

                await asyncio.sleep(2)

            except Exception as e:
                print(f"Ошибка при парсинге автора {author_name}: {e}")

        # Формируем итоговый объект
        review_data = {
            "Дата": review_date,
            "Оценка": rating,
            "Текст": review_text.replace("Читать весь отзыв", "").strip(),
            "Url": review_link,
            "Автор": author_name,
            "Url_Автора": author_link,
            "Дата регистрации": reg_date,
            "Кол-во отзывов": author_reviews_count,
            "Кол-во комментариев": author_comments_count,
            "Есть ответ ОП": has_op_response,
            "Дата ответа ОП": op_response_date
        }

        results.append(review_data)
        await append_data_to_sheet_scope(service, ss_id, project, review_data)
        await asyncio.sleep(3)

    return review_cards


async def check_otzovik(service, link, pattern, criteria, ss_id, project, driver):
    global recorded

    blocks = await blocks_otzovik(driver, link, service)
    if blocks == 'Next...':
        return 'Next...'

    elif blocks == None:
        return None

    len_b = len(blocks)

    if len_b == 0:
        print('- No blocks')
        return None

    links = await pars_url(service, ss_id, project)
    for block in blocks:
        try:
            url_answer = block.find_element(By.CSS_SELECTOR, 'meta[itemprop="url"]').get_attribute('content')
        except:
            url_answer = block.find_element(By.CSS_SELECTOR, 'meta[itemprop="url"]')

        if url_answer in links:
            print("Такой комментарий уже отмечен")
            continue

        try:
            date_content = block.find_element(By.CSS_SELECTOR, "div.review-postdate").get_attribute('content')

        except:
            date_content = block.find_element(By.CSS_SELECTOR, "div.review-postdate")

        #print("Date_content", date_content)
        date = datetime.strptime(date_content, "%Y-%m-%dT%H:%M:%S%z")
        date = date.replace(tzinfo=None)  # offset-naive
        formatted_date = date.strftime("%d.%m.%Y")

        if (current_date - date) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней. = {date}')
            return 'Next'

        author = block.find_element(By.CSS_SELECTOR, 'span[itemprop="name"]').text
        feedback = block.find_element(By.CSS_SELECTOR, "div.review-body-wrap").text

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

            recorded += 1

        except:
            print('No generate!')

async def main_otzovik():
    project = 'AlfaBank'
    p, browser, context, page = await get_playwright(headless=False, proxy_type='ru', stealth=True,
                                                     blocked_resource=False)

    service = await get_service()
    ss_id = '1mWKEZmrjrf2Ui2nGBD0nEZAR9uWPDMssJCu-40o_cd4'
    df = await read_table_id(service, ss_id, 'links')
    print(df)

    global lists

    try:
        df_project = await read_table_id(service, ss_id, project)
        lists = df_project['Url'].to_list()
    except:
        lists = []

    for idx, row in df.iterrows():
        p_2, browser_2, context_2, page_2 = await get_playwright(headless=False,
                                                                 proxy_type='ru',
                                                                 stealth=True,
                                                                 blocked_resource=False)

        link = row['link']
        try:
            pg = int(row['last_page'])
        except:
            pg = 1

        if 'otzovik' in link:
            while True:
                url = f'{link}{pg}/'
                await page.goto(url)
                await check_captcha(page)
                #await solve_captcha(page)

                datas = await full_blocks_otzovik(service, ss_id, project, page, page_2)
                len_d = len(datas)

                #to_dict = await transform_reviews_to_dict(datas)
                #await append_data_to_sheet_scopes(service, ss_id, project, to_dict)

                await append_data_to_sheet_cell(service, ss_id, "links", 'last_page', idx+2, pg)
                pg += 1

                if len_d < 39:
                    break

        try:
            await p_2.stop()
        except:
            pass



if __name__ == '__main__':


    asyncio.run(main_otzovik())
    print('The End!')