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
from utils.central_module import get_local_ip, wait_for_portal, proxy_status
from utils.constants import TABLES_LIST
from utils.gs_editor import get_service, pars_url, get_table_scope, write_log_sheet, append_data_to_sheet_scope, \
    append_data_to_sheet_cell
from utils.user_agent import get_selenium_proxy
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

local_ip = asyncio.run(get_local_ip())
# if '176.124.192' in local_ip:
#     headless = False
#     proxy_on = True
#
# else:
headless = False
proxy_on = False

recorded = 0

# print(f'- local_ip Otzovik: {local_ip} {headless} {proxy_on}')

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

async def check_otzovik(service, link, pattern, criteria, ss_id, project, driver):
    global recorded

    print(f'Link: {link}')
    try:
        print('--- Get 1.0')
        driver.get(link)

    except:
        print('--- Get 1.1')
        #driver = await get_selenium_proxy(link, headless=headless, proxy=proxy_on)
        driver = await get_selenium_proxy(link, headless=headless, proxy=proxy_on)

    if '176.124' in local_ip:
        driver = await captcha_check(driver) #обработка капчи
        if not driver:
            print('- Error Driver 1')
            return

    if '46.39.21.228' in local_ip:
        driver = await captcha_check(driver) #обработка капчи
        if not driver:
            print('- Error Driver 2')
            return

    await wait_for_portal()  # Время ожидания

    try:
        breadcrumbs = driver.find_element(By.CSS_SELECTOR, 'div.page-caption').text
        if 'Ошибка' in breadcrumbs:
            print(f"- {breadcrumbs}")
            return 'Next ...'

    except Exception as Ex:
        print(f"--- Error OTZ {Ex}")

    if 'order=date_desc' not in link:
        top_link = await get_top_link(driver)

        if top_link:
            datas = {'project': project,
                     'url': link,
                     'top_url': top_link}

            await append_data_to_sheet_scope(service, ss_id, 'unique_url', datas)
            try:
                print('--- Get 2.0')
                driver.get(top_link)
            except:
                print('--- Get 2.1')
                #driver = await get_selenium_proxy(top_link, headless=headless, proxy=proxy_on)
                driver = await get_selenium_proxy(top_link, headless=headless, proxy=proxy_on)
                driver = await captcha_check(driver)  # обработка капчи
                if not driver:
                    print('-- Error Driver')
                    return

        else:
            print('--- No top link')
            return driver

    else:
        print('- Это уже топовая ссылка.')

    n = 0
    len_b = 0
    while n < 10:
        try:
            blocks = driver.find_elements(By.CSS_SELECTOR, 'div[itemprop="review"]')
            len_b = len(blocks)
            print(f'Len_b: {len_b}')
            if len_b == 0:
                return 'Next...'

            break

        except:
            print(f'--- driver refresh')
            driver.refresh()
            await asyncio.sleep(5)
            n += 1

            if n == 10:
                print('- n == 10')
                return None

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

    driver = None
    if proxy_active == 'Active':
        # print(">>> Start WinProxy...")
        # await set_windows_proxy()
        # await asyncio.sleep(5)

        print('>>> Start Selenium...')
        #driver = await get_selenium_proxy(headless=headless, proxy=proxy_on)
        driver = await get_selenium_proxy(headless=headless, proxy=proxy_on)

    print('local_ip', local_ip)

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
                                                f'Proxy {proxy_active}')
                break

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
                    driver.quit()
                    #driver = await get_selenium_proxy(headless=headless, proxy=proxy_on)
                    driver = await get_selenium_proxy(headless=headless, proxy=proxy_on)

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

    url = 'https://otzovik.com/review_15376402.html'

    service = await get_service()
    #playwright, browser, page = await get_playwright(url, headless=False)

    driver = await get_selenium_proxy(url, headless=False)
    await check_otzovik(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", 1, driver)

if __name__ == '__main__':
    #asyncio.run(tst_otzovik())
    asyncio.run(main_otzovik())
    print('The End!')