import asyncio
import os
import random
import sys
import time
from datetime import datetime, timedelta

import pandas as pd
import requests
from dateutil import parser

from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from utils.anticaptcha import SendCaptcha

from playwright._impl._errors import TargetClosedError

from utils.ai_module import generate_and_white
from utils.central_module import wait_for_portal, proxy_status, is_running_in_container, get_local_ip
from utils.constants import TABLES_LIST, empty_data, months
from utils.gs_editor import get_service, pars_url, read_table_id, write_log_sheet, append_data_to_sheet_scope, \
    append_data_to_sheet_cell, read_table_id, append_data_to_sheet_scopes
from utils.user_agent import get_selenium_proxy, get_playwright
from utils.proxy_bridge import set_windows_proxy

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

corn_folder = os.path.dirname(os.path.dirname(__file__))

current_date = datetime.now()
current_year = current_date.year

record_date = current_date.strftime("%d.%m.%Y")

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)
days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))
captcha_key = os.environ.get("CAPTCHA_KEY")

ss_id = TABLES_LIST['zoom']

recorded = 0
headless = True
proxy_on = True


async def cleanup_captcha_images():
    temp_path = os.path.join(corn_folder, 'temp')
    if not os.path.isdir(temp_path):
        return

    for name in os.listdir(temp_path):
        if 'captcha_image_' in name:
            path = os.path.join(temp_path, name)
            try:
                os.remove(path)
                print(f'--- Removed {path}')
            except OSError as ex:
                print(f'--- Remove error {path}: {ex}')


async def get_top_link_pw(page):
    try:
        top_link_content = await page.query_selector('h1.product-name a')
        if top_link_content:
            return await top_link_content.get_attribute('href')
    except Exception as ex:
        print(f'--- func No top link: {ex}')
    return None


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


async def _solve_recaptcha_pw(page) -> bool:
    if not captcha_key:
        return False

    try:
        from playwright_captcha import TwoCaptchaSolver, CaptchaType, FrameworkType
        from twocaptcha import AsyncTwoCaptcha
    except ImportError:
        print('--- playwright_captcha not installed')
        return False

    from utils.anticaptcha import get_captcha_servers

    for server in get_captcha_servers():
        try:
            captcha_client = AsyncTwoCaptcha(captcha_key, server=server)
            async with TwoCaptchaSolver(
                framework=FrameworkType.PLAYWRIGHT,
                page=page,
                async_two_captcha_client=captcha_client,
            ) as solver:
                await solver.solve_captcha(
                    captcha_container=page,
                    captcha_type=CaptchaType.RECAPTCHA_V2,
                )
            return True
        except Exception as ex:
            print(f'--- reCAPTCHA solve error ({server}): {ex}')

    return False


async def _captcha_image_present(page) -> bool:
    if await page.locator('img#captcha-img').count() > 0:
        return True

    input_el = await page.query_selector('input[type="text"]')
    if not input_el:
        return False

    imgs = await page.query_selector_all('img[src]')
    return len(imgs) == 1


async def solve_captcha_pw(page) -> bool:
    """Решение капчи Otzovik через 2captcha (Playwright)."""
    if not captcha_key:
        print('--- CAPTCHA_KEY не задан')
        return False

    for attempt in range(10):
        if not await _captcha_image_present(page):
            recaptcha_frame = await page.locator('iframe[src*="recaptcha"]').count()
            if recaptcha_frame > 0:
                print('--- reCAPTCHA detected')
                if await _solve_recaptcha_pw(page):
                    await page.wait_for_timeout(3000)
                    if not await _captcha_image_present(page):
                        print('+++ reCAPTCHA solved')
                        return True
            else:
                print('--- No captcha')
                return True

        print(f'>>> Captcha found, solving... (attempt {attempt + 1})')

        captcha_img = await page.query_selector('img#captcha-img')
        if not captcha_img:
            imgs = await page.query_selector_all('img[src]')
            if len(imgs) == 1:
                captcha_img = imgs[0]

        if not captcha_img:
            return False

        temp_path = os.path.join(corn_folder, 'temp')
        os.makedirs(temp_path, exist_ok=True)
        file_link = os.path.join(temp_path, f'captcha_image_{int(time.time())}.png')
        await captcha_img.screenshot(path=file_link)
        print(f'-- Captcha screenshot: {file_link}')

        capcha_text = await sent_captcha(file_link)
        if os.path.exists(file_link):
            os.remove(file_link)

        if not capcha_text:
            print('--- 2captcha не вернул ответ')
            await page.reload(wait_until='domcontentloaded')
            await wait_for_portal()
            continue

        input_captcha = await page.query_selector('input[type="text"]')
        if not input_captcha:
            return False

        await input_captcha.fill(capcha_text)
        await asyncio.sleep(1)
        await input_captcha.press('Enter')
        await page.wait_for_timeout(3000)

        if not await _captcha_image_present(page):
            print('+++ Captcha solved')
            return True

        print('--- Captcha still present, retry...')
        await page.reload(wait_until='domcontentloaded')
        await wait_for_portal()

    return False


async def solve_captcha(page):
    return await solve_captcha_pw(page)


async def check_captcha(page):
    return await solve_captcha_pw(page)


async def sent_captcha(file_link):
    print('--- Send captcha...')
    anti = SendCaptcha(file_link)
    return await anti.normal_captcha()


async def normalize_otzovik_date(date_str):
    """
    Преобразует строковую дату Otzovik в формат dd.mm.YYYY.
    """
    if not date_str or not isinstance(date_str, str):
        return date_str

    today = datetime.now()
    date_str = date_str.lower().strip()

    if date_str == 'сегодня':
        return today.strftime('%d.%m.%Y')
    if date_str == 'вчера':
        return (today - timedelta(days=1)).strftime('%d.%m.%Y')

    weekdays = {
        'понедельник': 0, 'вторник': 1, 'среда': 2,
        'четверг': 3, 'пятница': 4, 'суббота': 5, 'воскресенье': 6
    }

    if date_str in weekdays:
        target_weekday = weekdays[date_str]
        current_weekday = today.weekday()
        days_ago_val = (current_weekday - target_weekday) % 7
        if days_ago_val == 0:
            days_ago_val = 7
        res_date = today - timedelta(days=days_ago_val)
        return res_date.strftime('%d.%m.%Y')

    parts = date_str.split()
    if len(parts) >= 2:
        try:
            day = int(parts[0])
            month_name = parts[1][:3]
            month = months.get(month_name, 1)

            if len(parts) == 3:
                year = int(parts[2])
            else:
                year = today.year

            return f"{day:02d}.{month:02d}.{year}"
        except (ValueError, IndexError):
            return date_str

    return date_str


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

    status = await check_captcha(page)
    if status == False:
        return None

    text = await page.locator('div.item-right').inner_text()
    await asyncio.sleep(2)
    return text


async def blocks_otzovik(page, page2, links, min_rating, max_rating):
    blocks = await page.locator('div[class="item status4 mshow0"]').all()

    datas = await empty_data()
    datas['len'] = []

    for block in blocks:
        rating = int(await block.locator('div[class="rating-score tooltip-right"]').inner_text())
        datas['len'].append(rating)

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


async def full_blocks_otzovik(service, ss_id, project, page, page_2, page_3):
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

        if review_date:
            review_date_raw = parser.parse(review_date)
            review_year = review_date_raw.year
        else:
            review_year = None

        if review_year != current_year:
            return 'end'

        # Оценка
        rating_el = await card.query_selector('.rating-score span')
        rating = await rating_el.inner_text() if rating_el else None

        # Текст отзыва (тизер)
        text_el = await card.query_selector('div.item-right')
        review_text = await text_el.inner_text()

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

        await page_3.goto(review_link)

        status = await check_captcha(page_3)
        if status == False:
            return results

        comment_author_wrap = await page_3.query_selector_all('div.comment-author-wrap')
        len_comment = len(comment_author_wrap)
        print(f'len comments = {len_comment}')

        has_op_response = "Нет"
        op_response_date = ""

        if len_comment > 0:
            for caw in comment_author_wrap:
                official_span = await caw.query_selector('span.product-official')
                if official_span and (await official_span.inner_text()).strip() == 'Официальный представитель':
                    has_op_response = "Да"

                    # Получаем строку таймстемпа из атрибута (исправлено get_attribute)
                    date_element = await caw.query_selector('div.comment-postdate.ts')
                    if date_element:
                        ts_str = await date_element.get_attribute('data-ts')

                        # Конвертируем строку в число, а затем в нужный формат даты
                        timestamp = int(ts_str)
                        op_response_date = datetime.fromtimestamp(timestamp).strftime('%d.%m.%Y')

                    break

        # --- Сбор данных со страницы автора (page_2) ---
        reg_date = None
        author_reviews_count = 0
        author_comments_count = 0

        if author_link:
            try:
                # Переходим на страницу автора во втором окне
                await page_2.goto(author_link)

                status = await check_captcha(page_2)
                if status == False:
                    return results

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
            "Текст": review_text,
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


async def check_otzovik(service, link, pattern, criteria, ss_id, project, page, page_2, source_link=None):
    global recorded

    if source_link is None:
        source_link = link

    on_list_page = False
    print(f'\nLink: {link}')
    await page.goto(link, wait_until='domcontentloaded')
    await page.wait_for_timeout(2000)

    if not await check_captcha(page):
        return None

    caption_el = await page.query_selector('div.page-caption')
    if caption_el:
        caption = await caption_el.inner_text()
        if 'Ошибка' in caption:
            print(caption)
            if '/reviews/' in link and source_link.rstrip('/') != link.rstrip('/') and '/review_' in source_link:
                print('--- Устаревший top_url, читаем со страницы отзыва')
                await page.goto(source_link, wait_until='domcontentloaded')
                await page.wait_for_timeout(2000)
                if not await check_captcha(page):
                    return None
                top_link = await get_top_link_pw(page)
                if not top_link:
                    print('--- No top link')
                    return None
                if not top_link.startswith('http'):
                    top_link = f'https://otzovik.com{top_link}'
                await append_data_to_sheet_scope(service, ss_id, 'unique_url', {
                    'project': project,
                    'url': source_link,
                    'top_url': top_link,
                })
                print(f'-- Обновлён TOP link: {top_link}')
                link = top_link.split('?')[0].rstrip('/') + '/?order=date_desc'
                await page.goto(link, wait_until='domcontentloaded')
                await page.wait_for_timeout(2000)
                if not await check_captcha(page):
                    return None
                caption_el = await page.query_selector('div.page-caption')
                if caption_el:
                    caption = await caption_el.inner_text()
                    if 'Ошибка' in caption:
                        print(caption)
                        return 'Next...'
                on_list_page = True
            else:
                return 'Next...'

    if not on_list_page:
        list_url = link
        if '/reviews/' in link and 'order=date_desc' not in link:
            list_url = link.split('?')[0].rstrip('/') + '/?order=date_desc'
            await page.goto(list_url, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)
            if not await check_captcha(page):
                return None

        elif 'order=date_desc' not in link:
            top_link = await get_top_link_pw(page)
            if not top_link:
                print('--- No top link')
                return None

            if not top_link.startswith('http'):
                top_link = f'https://otzovik.com{top_link}'

            await append_data_to_sheet_scope(service, ss_id, 'unique_url', {
                'project': project,
                'url': link,
                'top_url': top_link,
            })
            print('-- Record TOP link')
            list_url = top_link.split('?')[0].rstrip('/') + '/?order=date_desc'
            await page.goto(list_url, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)
            if not await check_captcha(page):
                return None
        else:
            print('- Это уже топовая ссылка.')

    review_cards = await page.query_selector_all('div.item.status4.mshow0')
    if not review_cards:
        review_cards = await page.query_selector_all('div[itemprop="review"]')

    len_b = len(review_cards)
    print(f'Len_b = {len_b}')
    if len_b == 0:
        return None

    links = await pars_url(service, ss_id, project)

    for card in review_cards:
        print('****************************')

        review_link = None
        link_el = await card.query_selector('a.review-title')
        if link_el:
            href = await link_el.get_attribute('href')
            if href:
                review_link = f'https://otzovik.com{href}' if href.startswith('/') else href

        if not review_link:
            meta_el = await card.query_selector('meta[itemprop="url"]')
            if meta_el:
                review_link = await meta_el.get_attribute('content')

        if not review_link:
            continue

        print(review_link)

        if review_link in links:
            print('Отзыв уже есть в таблице')
            continue

        formatted_date = None
        target_date = None

        date_el = await card.query_selector('div.review-postdate')
        if date_el:
            content = await date_el.get_attribute('content')
            if content:
                try:
                    target_date = datetime.strptime(content, "%Y-%m-%dT%H:%M:%S%z").replace(tzinfo=None)
                    formatted_date = target_date.strftime("%d.%m.%Y")
                except ValueError:
                    pass

        if not formatted_date:
            span_el = await card.query_selector('.review-postdate span')
            if span_el:
                date_str = await span_el.inner_text()
                formatted_date = await date_convert(date_str)
                try:
                    target_date = datetime.strptime(formatted_date, "%d.%m.%Y")
                except ValueError:
                    continue

        if not target_date:
            continue

        if (current_date - target_date) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней = {formatted_date}.')
            return "Next..."

        author_el = await card.query_selector('span[itemprop="name"]')
        if not author_el:
            author_el = await card.query_selector('a.user-login')
        if not author_el:
            continue
        author = (await author_el.inner_text()).strip()

        feedback = await get_feedback(page_2, review_link)
        if not feedback:
            print('--- Пустой текст отзыва')
            continue

        await generate_and_white(
            service=service,
            url_answer=review_link,
            author=author,
            formatted_date=formatted_date,
            ss_id=ss_id,
            project=project,
            feedback=feedback,
            pattern=pattern,
            criteria=criteria,
        )
        recorded += 1

    return 'OK!'


async def start_browser():
    p, browser, context, page = await get_playwright(
        headless=headless,
        proxy=proxy_on,
        proxy_type='ru',
        stealth=True,
        blocked_resource=False,
    )

    return p, browser, context, page


async def main_otzovik():
    global headless, proxy_on, recorded

    service = await get_service()

    headless = await is_running_in_container()
    proxy_on = True
    print(f'-- Otzovik: headless={headless}, proxy={proxy_on}')

    proxy_active = await proxy_status()
    print(f'+ Proxy status: {proxy_active}')

    p, browser, context, page = await start_browser()
    p_2, browser_2, context_2, page_2 = await start_browser()

    try:
        df = await read_table_id(service, ss_id, 'zoom')
        idx_num_row = df.index[df['Проект'] == 'Кол-во строк'].tolist()[0]
        df_counts = pd.Series(df.iloc[idx_num_row].values, index=df.columns).reset_index()
        df_counts[0] = pd.to_numeric(df_counts[0], errors='coerce')
        df_counts = df_counts.dropna(subset=[0])
        df_counts = df_counts.sort_values(by=0)
        list_ = df_counts['index'].to_list()

        df_uniq = await read_table_id(service, ss_id, 'unique_url')
        df_logs = await read_table_id(service, ss_id, 'logs')

        df_daily = await read_table_id(service, ss_id, 'daily_data')
        df_daily = df_daily[df_daily['date'] == record_date]
        daily_links = set(df_daily['url'].tolist())

        for project in list_:
            if 'Проект' in project:
                continue

            df_mini = df[project]
            df_mini_pattern = df_mini[df_mini.str.contains('Пример реакции', na=False)]
            df_mini_criteria = df_mini[df_mini.str.contains('Особые критерии', na=False)]
            df_mini = df_mini[df_mini.str.contains('http', na=False)]
            df_mini = df_mini.drop_duplicates().reset_index()

            df_link_list = df_mini[project].to_list()
            otz_link = [i for i in df_link_list if 'otzovik' in i]
            len_otz = len(otz_link)
            if len_otz == 0:
                print(f'{project} next...')
                continue

            print(f'\n ---> {project} Otzovik link = {len_otz} <---')
            random.shuffle(df_link_list)

            len_df = len(df_link_list)
            print(f'\n========================= Project = {project} = Len ({len_df})==============================')

            project_otzovik = f'otzovik_{project}'
            filtered_logs = df_logs[df_logs['service_name'] == project_otzovik]
            if not filtered_logs.empty:
                idx_logs = filtered_logs.index[0]

                if proxy_active != 'Active':
                    await append_data_to_sheet_cell(
                        service, ss_id, 'logs', 'status', idx_logs + 2,
                        f'Proxy {proxy_active}: {record_date}',
                    )
                else:
                    await append_data_to_sheet_cell(
                        service, ss_id, 'logs', 'status', idx_logs + 2,
                        f'Proxy {proxy_active}',
                    )

                date_logs = df_logs.loc[idx_logs, 'date']
                if date_logs == record_date:
                    continue

            start_time = time.time()
            list_links = []
            record = False
            recorded = 0

            for idx, link in enumerate(df_link_list):
                left = len_df - df_link_list.index(link)
                print(
                    f'\n*************************{idx}*({left})*{project}*************************\n'
                    f'----------------- {link} ----------------'
                )

                if 'otzovik' in link:
                    if link in daily_links:
                        print('Эта ссылка сегодня уже отработана')
                        continue

                    record = True
                    source_link = link
                    top_df = df_uniq[(df_uniq['project'] == project) & (df_uniq['url'] == link)].reset_index(drop=True)

                    if not top_df.empty:
                        print('Есть общая ссылка на статью')
                        link = top_df.iloc[-1]['top_url']

                    if link in list_links:
                        print('Ссылка уже проверена.')
                        continue

                    list_links.append(link)

                    try:
                        await check_otzovik(
                            service=service,
                            link=link,
                            pattern=df_mini_pattern,
                            criteria=df_mini_criteria,
                            ss_id=ss_id,
                            project=project,
                            page=page,
                            page_2=page_2,
                            source_link=source_link,
                        )
                    except TargetClosedError:
                        print('--- Browser closed')

                        if page.is_closed():
                            print('--- Restart main browser')
                            try:
                                await browser.close()
                            except Exception:
                                pass
                            try:
                                await p.stop()
                            except Exception:
                                pass
                            p, browser, context, page = await start_browser()

                        if page_2.is_closed():
                            print('--- Restart feedback browser')
                            try:
                                await browser_2.close()
                            except Exception:
                                pass
                            try:
                                await p_2.stop()
                            except Exception:
                                pass
                            p_2, browser_2, context_2, page_2 = await start_browser()

                        try:
                            await check_otzovik(
                                service=service,
                                link=link,
                                pattern=df_mini_pattern,
                                criteria=df_mini_criteria,
                                ss_id=ss_id,
                                project=project,
                                page=page,
                                page_2=page_2,
                                source_link=source_link,
                            )
                        except TargetClosedError:
                            print('--- Browser dead again, skip link')
                            continue

                    new_daily_data = {'date': record_date, 'url': source_link}
                    await append_data_to_sheet_scope(service, ss_id, 'daily_data', new_daily_data)
                    daily_links.add(source_link)

            if record and recorded > 0:
                finish_sec = time.time() - start_time
                datas = {
                    'service_name': project_otzovik,
                    'count': len_otz,
                    'date': record_date,
                    'time': finish_sec,
                    'recorded': recorded,
                }
                print('datas', datas)
                await write_log_sheet(service, ss_id, 'logs', datas)

    finally:
        await cleanup_captcha_images()

        try:
            await browser_2.close()
        except Exception:
            pass
        try:
            await p_2.stop()
        except Exception:
            pass
        try:
            await browser.close()
        except Exception:
            pass
        try:
            await p.stop()
        except Exception:
            pass



if __name__ == '__main__':
    async def _run():

        await main_otzovik()

    asyncio.run(_run())
    print('The End!')