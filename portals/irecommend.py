import asyncio
import random
import time

from datetime import datetime, timedelta

import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils.central_module import get_local_ip, wait_for_portal
from utils.constants import TABLES_LIST
from utils.gs_editor import pars_url, append_data_to_sheet_scope, get_service, get_table_scope, write_log_sheet
from utils.ai_module import generate_and_white
from utils.user_agent import get_soup, extract_main_site, get_soup_anticloud, get_playwright, get_selenium_proxy
import textwrap

import os
from dotenv import load_dotenv

current_date = datetime.now().strftime("%d.%m.%Y")

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)
days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))
ss_id = TABLES_LIST['zoom']

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

async def check_irecommend(service, link, pattern, criteria, ss_id, project, driver):
    timeout = 10000
    driver.get(link)
    await wait_for_portal()

    element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h1[class="largeHeader"]')))
    print('---', element.text)

    domen = await extract_main_site(link)
    top_block_content = driver.find_element(By.CSS_SELECTOR, 'h1[class="largeHeader"]')
    top_block = top_block_content.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
    top_url = domen + top_block + "?new=1"
    print(top_url)

    input('2')

    try:
        await page.wait_for_selector('h1[class="largeHeader"]', timeout=timeout)

        top_url = await page.query_selector('h1[class="largeHeader"]')
        print(f'Получение главной темы на основании комментов.')
        top_block_content = await top_url.query_selector('a')
        top_block = await top_block_content.get_attribute('href')
        top_url = domen + top_block + "?new=1"

    except:
        print('Это уже топовая ссылка')
        top_url = link

    print(top_url)

    await page.goto(top_url)











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






async def main_irecommend():
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

    driver = await get_selenium_proxy('https://irecommend.ru/')

    for project in list_:
        if 'Проект' in project:
            continue

        #Если дата не совпадает с сегодняшней
        # host_logs = ''
        # filtered_logs = df_logs[df_logs['service_name'] == project]
        # if not filtered_logs.empty:
        #     idx_logs = filtered_logs.index[0]
        #
        #     #Пропуск по дате
        #     date_logs = df_logs.loc[idx_logs, 'date']
        #     if date_logs == current_date:
        #         #print()
        #         continue
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
        random.shuffle(df_link_list)

        len_df = len(df_link_list)
        print(f'\n========================= Project = {project} = Len ({len_df})==============================')

        start_time = time.time()
        list_links = []

        record = False
        for idx, link in enumerate(df_link_list):
            left = len_df - df_link_list.index(link)
            print(
                f'\n*************************{idx}*({left})***************************\n----------------- {link} ----------------')

            if 'irecommend' in link:
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

                await check_irecommend(service=service,
                                       link=link,
                                       pattern=df_mini_pattern,
                                       criteria=df_mini_criteria,
                                       ss_id=ss_id,
                                       project=project,
                                       driver=driver)

        if record:
            finish_sec = time.time() - start_time
            datas = {'service_name': 'Only_irecommend',
                    'count': len_df,
                    'date': current_date,
                    'time': finish_sec}

            print('datas', datas)
            await write_log_sheet(service, ss_id, 'logs', datas)

    driver.close()















if "__main__" in __name__:
    asyncio.run(main_irecommend())



