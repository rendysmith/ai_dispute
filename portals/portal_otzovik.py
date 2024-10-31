import asyncio
import os
import random
import sys
import time
from datetime import datetime, timedelta

import pandas as pd
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from twocaptcha import TwoCaptcha

from utils.ai_module import generate_and_white
from utils.central_module import get_local_ip, wait_for_portal
from utils.constants import TABLES_LIST
from utils.gs_editor import get_service, pars_url, get_table_scope, write_log_sheet, append_data_to_sheet_scope
from utils.user_agent import get_selenium_proxy

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

async def get_top_link(driver):
    try:
        top_link_content = driver.find_element(By.CSS_SELECTOR, 'h1.product-name')
        top_link = top_link_content.find_element(By.CSS_SELECTOR, 'a')
        return top_link.get_attribute('href')
    except:
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
        print(result)
        if result.get('code'):
            print(result['code'])
            return result['code']

        await asyncio.sleep(1)
        n += 1
        print(f'nC = {n}')

    return None

async def captcha_check(driver):
    n = 0
    while n < 10:
        try:
            capcha = driver.find_elements(By.CSS_SELECTOR, 'img[src]')

            len_c = len(capcha)
            if len_c != 1:
                return driver

            number_file = int(time.time())
            file_link = os.path.join(corn_folder, 'temp', f'captcha_image_{number_file}.png')
            # Сохранение скриншота капчи
            capcha.screenshot(file_link)
            print("Скриншот капчи сохранен.")

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

        except:
            n += 1
            await asyncio.sleep(3)

    return driver

async def check_otzovik(service, link, pattern, criteria, ss_id, project, driver):
    print(f'Link: {link}')
    driver.get(link)

    driver = await captcha_check(driver) #обработка капчи
    await wait_for_portal()  # Время ожидания

    try:
        breadcrumbs = driver.find_element(By.CSS_SELECTOR, 'div.page-caption').text
        if 'Ошибка' in breadcrumbs:
            print(breadcrumbs)
            return 'Next ...'

    except:
        pass

    if 'order=date_desc' not in link:
        top_link = await get_top_link(driver)

        if top_link:
            datas = {'project': project,
                     'url': link,
                     'top_url': top_link}

            await append_data_to_sheet_scope(service, ss_id, 'unique_url', datas)
            driver.get(top_link)

        else:
            return

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
                return None

    if len_b == 0:
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
        except:
            print('No generate!')

async def main_otzovik():
    local_ip = await get_local_ip()
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

    driver = await get_selenium_proxy()

    for project in list_:
        if 'Проект' in project:
            continue

        #Если дата не совпадает с сегодняшней
        host_logs = ''
        project_otzovik = f'{project}_otzovik'
        filtered_logs = df_logs[df_logs['service_name'] == project_otzovik]
        if not filtered_logs.empty:
            idx_logs = filtered_logs.index[0]

            #Пропуск по дате
            date_logs = df_logs.loc[idx_logs, 'date']
            if date_logs == current_date:
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

        random.shuffle(df_link_list)

        len_df = len(df_link_list)
        print(f'\n========================= Project = {project} = Len ({len_df})==============================')

        start_time = time.time()
        list_links = []

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

                status = await check_otzovik(service=service,
                                       link=link,
                                       pattern=df_mini_pattern,
                                       criteria=df_mini_criteria,
                                       ss_id=ss_id,
                                       project=project,
                                       driver=driver)

                if not status:
                    driver.quit()
                    driver = await get_selenium_proxy()

        if record:
            finish_sec = time.time() - start_time
            datas = {'service_name': project_otzovik,
                    'count': len_irec,
                    'date': record_date,
                    'time': finish_sec}

            print('datas', datas)
            await write_log_sheet(service, ss_id, 'logs', datas)

    driver.close()

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
    asyncio.run(tst_otzovik())
    #asyncio.run(main_otzovik())
    print('The End!')


# async def get_top_link(link):
#     try:
#         #soup = await get_soup(link)
#         soup = await get_soup_anticloud(link)
#
#         if not soup:
#             return False, False
#
#         top_link = soup.find('h1', {"class": "product-name"})
#         top_url = "https://otzovik.com" + top_link.find('a')['href'] + '?order=date_desc'
#         print("+ top_url", top_url)
#         return True, top_url
#
#     except TypeError as TE:
#         print(f"Error Top Link TE: {TE}")
#         traceback.print_exc()
#         return False, link
#
#     except Exception as Ex:
#         print(f"Error Top Link Ex: {Ex}")
#         traceback.print_exc()
#         return False, False
#
# async def check_otzovik_old(service, link, pattern, criteria, ss_id, project):
#     print(link)
#
#     status, top_url = await get_top_link(link)
#     if not top_url:
#         return 'Сайт не отдал данные!'
#
#     print(status, top_url)
#
#     if status:
#         datas = {'project': project,
#                  'url': link,
#                  'top_url': top_url}
#
#         await append_data_to_sheet_scope(service, ss_id, 'unique_url', datas)
#
#     #soup = await get_soup(top_url)
#     soup = await get_soup_anticloud(top_url)
#     if not soup:
#         return 'Сайт не отдал данные!'
#
#     blocks = soup.find_all("div", {"itemprop": "review"})
#     print('Len B', len(blocks))
#
#     if len(blocks) == 0:
#         return
#
#     links = await pars_url(service, ss_id, project)
#
#     for block in blocks:
#         try:
#             url_answer = block.find('meta', {'itemprop': "url"}).get('content')
#         except:
#             url_answer = block.find('meta', {'itemprop': "url"})
#
#         if url_answer in links:
#             print("Такой комментарий уже отмечен")
#             continue
#
#         try:
#             date_content = block.find("div", {"class": "review-postdate"}).get('content')
#         except:
#             date_content = block.find("div", {"class": "review-postdate"})
#
#         print("Date_content", date_content)
#         date = datetime.strptime(date_content, "%Y-%m-%dT%H:%M:%S%z")
#         date = date.replace(tzinfo=None)  # offset-naive
#
#         formatted_date = date.strftime("%d.%m.%Y")
#
#         if (current_date - date) > timedelta(days=days_ago):
#             print(f'--- Отзыв старше {days_ago} дней. = {date}')
#             return
#
#         author = block.find("span", {"itemprop": "name"}).text
#         feedback = block.find("div", {"class": "review-body-wrap"}).text
#
#         try:
#             await generate_and_white(service=service,
#                                      url_answer=url_answer,
#                                      author=author,
#                                      formatted_date=formatted_date,
#                                      ss_id=ss_id,
#                                      project=project,
#                                      feedback=feedback,
#                                      pattern=pattern,
#                                      criteria=criteria)
#         except:
#             print('No generate!')
#
# async def check_otzovik_py(service, link, pattern, criteria, ss_id, project, playwright, browser, page, skip=False):
#     timeout = 10000
#
#
#
#     input()
#
#
#
#
#     full_content = await page.content()
#     print(full_content)
#
#     try:
#         await page.wait_for_selector("center", timeout=timeout)
#         tech_content = await page.query_selector('center')
#         tech = await tech_content.text_content()
#
#         if 'Технический перерыв' in tech:
#             await asyncio.sleep(30)
#             return
#
#     except TimeoutError as TE:
#         await page.wait_for_selector('td[align="left"]', timeout=timeout)
#         capcha_content = await page.query_selector('td[align="left"]')
#
#         tech = await capcha_content.text_content()
#         print(tech)
#
#         #print('cont 1', await capcha_content)
#         txt1 =  await capcha_content.text_content()
#         txt2 = await capcha_content.inner_text()
#
#         print("txt1", txt1)
#         print("txt2", txt2)
#
#         capcha_link = await capcha_content.get_attribute('align')
#         print('get 1', capcha_link)
#
#         capcha_link = await capcha_content.get_attribute('scr')
#         print('get 2', capcha_link)
#
#         capcha_content = await capcha_content.query_selector('img')
#         capcha_link = await capcha_content.get_attribute('scr')
#         print('get 3', capcha_link)
#
#     except Exception as Ex:
#         print('No capcha')
#
#     input('Next...')
#
#     await page.wait_for_selector('h1', timeout=timeout)
#     title_page_content = await page.query_selector('h1')
#     title_page = await title_page_content.inner_text()
#
#     if title_page == 'Ошибка: Страница не найдена!':
#         print(title_page)
#         return
#
#     try:
#         await page.wait_for_selector('h1[class="product-name"]', timeout=timeout)
#         top_link_content_0 = await page.query_selector('h1[class="product-name"]')
#         top_link_content = await top_link_content_0.query_selector('a')
#
#         top_link = await top_link_content.get_attribute('href')
#
#         top_url = "https://otzovik.com" + top_link + '?order=date_desc'
#
#         print('Top url:', top_url)
#
#         if not top_url:
#             return 'Сайт не отдал данные!'
#
#         else:
#             datas = {'project': project,
#                      'url': link,
#                      'top_url': top_url}
#
#             await append_data_to_sheet_scope(service, ss_id, 'unique_url', datas)
#         await page.goto(top_url)
#
#     except:
#         print('This is top_url')
#
#     await page.wait_for_selector('div[itemprop="review"]', timeout=timeout)
#     blocks = await page.query_selector_all('div[itemprop="review"]')
#
#     len_b = len(blocks)
#     print('Len B', len_b)
#
#     if len_b == 0:
#         await browser.close()
#         await playwright.stop()
#         return
#
#     links = await pars_url(service, ss_id, project)
#
#     for block in blocks:
#         url_answer_content = await block.query_selector('meta[itemprop="url"]')
#         url_answer = await url_answer_content.get_attribute('content')
#         #print(url_answer)
#
#         if url_answer in links:
#             print("Такой комментарий уже отмечен")
#             continue
#
#         date_content = await block.query_selector('div[class="review-postdate"]')
#         date_full = await date_content.get_attribute('content')
#
#         #print("date_full", date_full)
#         date = datetime.strptime(date_full, "%Y-%m-%dT%H:%M:%S%z")
#         date = date.replace(tzinfo=None)  # offset-naive
#         #print(date)
#
#         formatted_date = date.strftime("%d.%m.%Y")
#         #print(formatted_date)
#
#         if (current_date - date) > timedelta(days=days_ago):
#             print(f'--- Отзыв старше {days_ago} дней. = {date}')
#             return
#
#         author_content = await block.query_selector('span[itemprop="name"]')
#         author = await author_content.inner_text()
#         #print(author)
#
#         feedback_content = await block.query_selector('div[class="review-body-wrap"]')
#         feedback = await feedback_content.inner_text()
#         #print(feedback)
#
#         if skip == False:
#             await generate_and_white(service=service,
#                                      url_answer=url_answer,
#                                      author=author,
#                                      formatted_date=formatted_date,
#                                      ss_id=ss_id,
#                                      project=project,
#                                      feedback=feedback,
#                                      pattern=pattern,
#                                      criteria=criteria)
#
#
#     await browser.close()
#     await playwright.stop()
