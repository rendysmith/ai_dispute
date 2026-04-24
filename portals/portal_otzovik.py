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
from twocaptcha import TwoCaptcha

from utils.ai_module import generate_and_white
from utils.central_module import wait_for_portal, proxy_status, get_hpo
from utils.constants import TABLES_LIST, empty_data
from utils.gs_editor import get_service, pars_url, get_table_scope, write_log_sheet, append_data_to_sheet_scope, \
    append_data_to_sheet_cell
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

ss_id = TABLES_LIST['zoom']

headless, proxy_on, only_text = asyncio.run(get_hpo())
headless = False

print(f"Headless = {headless}, proxy = {proxy_on}")

recorded = 0

# print(f'- local_ip Otzovik: {local_ip} {headless} {proxy_on}')

async def check_captcha(page):
    while True:
        captcha = page.locator('img[id="captcha-img"]')
        if await captcha.is_visible():
            print("--- Captcha!")

            # captcha_link_content = await page.locator("img[id='captcha-img']").get_attribute('src')
            # captcha_link = 'https://otzovik.com' + captcha_link_content
            # print(captcha_link)
            #
            # response = await page.request.get(captcha_link)
            #
            # # Сохраняем в файл
            # if response.ok:
            #     with open("captcha1.png", "wb") as f:
            #         f.write(await response.body())
            #     print("Капча сохранена!")

            captcha_element = page.locator("img[id='captcha-img']")

            captcha_path = f'{corn_folder}/downloaded_files/captcha_{int(time.time())}.png'
            await captcha_element.screenshot(path=captcha_path)

            captcha_text = await sent_captcha(captcha_path)
            print(captcha_text)

            # 1. Находим инпут (лучше использовать более точный селектор)
            input_field = page.get_by_placeholder("Введите код с картинки")

            # 2. Очищаем поле (на всякий случай) и вводим текст
            # fill() работает быстрее и надежнее для большинства капч
            await input_field.fill(captcha_text)

            # 3. Нажимаем Enter (обязательно с await)
            await input_field.press("Enter")

        else:
            print('--- Without captcha')
            break

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

async def sent_captcha(file_link):
    print('- Send captcha...')
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
    proxy_active = await proxy_status()
    print(f'Proxy status: {proxy_active}')

    driver = await get_selenium_proxy(headless=headless, proxy=proxy_on)

    service = await get_service()
    df = await get_table_scope(service, ss_id, 'zoom')
    #print(df)
    idx_num_row = df.index[df['Проект'] == 'Кол-во строк'].tolist()[0]
    print(idx_num_row)
    df_counts = pd.Series(df.iloc[idx_num_row].values, index=df.columns).reset_index()
    df_counts[0] = pd.to_numeric(df_counts[0], errors='coerce')
    # Удаляем строки с NaN значениями в указанной колонке
    df_counts = df_counts.dropna(subset=[0])
    df_counts = df_counts.sort_values(by=0)
    #print(df_counts)

    list_ = df_counts['index'].to_list()
    print(list_)
    #random.shuffle(list_)

    df_uniq = await get_table_scope(service, ss_id, 'unique_url')

    df_logs = await get_table_scope(service, ss_id, 'logs')
    print(df_logs)

    for project in list_:
        if 'Проект' in project:
            continue

        #Если дата не совпадает с сегодняшней
        host_logs = ''
        project_otzovik = f'otzovik_{project}'
        filtered_logs = df_logs[df_logs['service_name'] == project_otzovik]
        if not filtered_logs.empty:
            idx_logs = filtered_logs.index[0]

            if proxy_active != 'Active':
                await append_data_to_sheet_cell(service, ss_id, 'logs', 'status', idx_logs + 2,
                                                f'Proxy {proxy_active}: {record_date}')

            else:
                await append_data_to_sheet_cell(service, ss_id, 'logs', 'status', idx_logs + 2,
                                                f'Proxy {proxy_active}')

            #Пропуск по дате
            date_logs = df_logs.loc[idx_logs, 'date']
            if date_logs == record_date:
                #print()
                continue
        #
        #     #Пропуск по IP
        #     host_logs = df_logs.loc[idx_logs, 'reserve']
        #     if host_logs != local_ip:
        #         print('Skip:', host_logs, local_ip)
        #         continue
        #
        # else:
        #     print(f"No logs found for service: {project}")

        df_mini = df[project]
        #print(len(df_mini))

        df_mini_pattern = df_mini[df_mini.str.contains('Пример реакции', na=False)]
        df_mini_criteria = df_mini[df_mini.str.contains('Особые критерии', na=False)]

        # Filter rows that contain 'http://'
        df_mini = df_mini[df_mini.str.contains('http', na=False)]

        # Remove duplicates
        # Удаляем дубликаты
        df_mini = df_mini.drop_duplicates().reset_index()

        df_link_list = df_mini[project].to_list()
        irec_link = [i for i in df_link_list if 'otzovik' in i]
        len_irec = len(irec_link)
        if len_irec == 0:
            print(f'{project} next...')
            continue

        print(f'+++++++++++ {project} Irec link = {len_irec} ++++++++++++++')

        random.shuffle(df_link_list)

        len_df = len(df_link_list)
        print(f'\n========================= Project = {project} = Len ({len_df})==============================')

        start_time = time.time()
        list_links = []

        global recorded
        recorded = 0

        record = False
        for idx, link in enumerate(df_link_list):
            left = len_df - df_link_list.index(link)
            print(
                f'\n*************************{idx}*({left})*{project}**************************\n----------------- {link} ----------------')

            if 'otzovik' in link:
                record = True
                top_df = df_uniq[(df_uniq['project'] == project) & (df_uniq['url'] == link)].reset_index(drop=True)
                # print(top_df)

                if not top_df.empty:
                    print('Есть общая ссылка на статью')
                    link = top_df.loc[0, 'top_url']

                if link in list_links:
                    print('Ссылка уже проверена.')
                    continue

                else:
                    list_links.append(link)

                timeout_seconds = 5 * 60  # 5 minuts
                try:
                    status = await asyncio.wait_for(
                        check_otzovik(service=service,
                                      link=link,
                                      pattern=df_mini_pattern,
                                      criteria=df_mini_criteria,
                                      ss_id=ss_id,
                                      project=project,
                                      driver=driver),
                    timeout= timeout_seconds) #5 минут.

                except asyncio.TimeoutError:
                    status = None
                    print(f"Function 'check_otzovik' timed out after {timeout_seconds / 60} minutes.")

                except Exception as e:
                    status = None
                    print(f"An unexpected error occurred: {e}")

                if not status:
                    # driver.quit()
                    # #driver = await get_selenium_proxy(headless=headless, proxy=proxy_on)
                    # driver = await get_selenium_proxy(headless=headless, proxy=proxy_on)
                    pass

        if record:
            finish_sec = time.time() - start_time
            datas = {'service_name': project_otzovik,
                    'count': len_irec,
                    'date': record_date,
                    'time': finish_sec,
                    'recorded': recorded}

            print('datas', datas)
            await write_log_sheet(service, ss_id, 'logs', datas)

    if driver:
        driver.quit()

async def tst_otzovik():
    # file_link = '/home/andy/PycharmProjects/sidorin/ai_one_off/temp/captcha_image_1729773670.png'
    # capcha_text = await sent_captcha(file_link)
    # print(capcha_text)
    # input('Wait...')

    p, browser, context, page = await get_playwright(headless=False, blocked_resource=False)

    url = 'https://otzovik.com/reviews/elektronniy_polis_osago_sber_strahovanie/2/?order=date_desc'

    await page.goto(url)

    await blocks_otzovik(context, page, 4, 5)


if __name__ == '__main__':
    #asyncio.run(tst_otzovik())
    asyncio.run(tst_otzovik())
    print('The End!')