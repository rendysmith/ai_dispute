import os
import time
from datetime import datetime, timedelta
from pprint import pprint

from dotenv import load_dotenv

import asyncio
from selenium.webdriver.common.by import By
from urllib.parse import urlparse

from portals.portal_pikaby import blocks_pikabu, check_pikaby
from portals.youtube import check_youtube
from portals.portal_otvet import check_otvet
from portals.portal_vk import check_vk

from utils.ai_module import generate_and_white
from utils.central_module import get_hpo
from utils.gs_editor import read_table_id, get_service, write_log_sheet
from utils.constants import TABLES_LIST

from portals.portal_vk import blocks_vk
from portals.portal_dzen import check_dzen
from utils.user_agent import get_selenium_proxy

ss_id = TABLES_LIST['zoom']
now = datetime.now()

current_date = now.strftime("%d.%m.%Y")

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)
days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

project = 'AlphaPet'

async def get_domen(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    if domain != '':
        return domain

    else:
        return

async def pikabu_parser(service, uniq_links, link, pattern, criteria, driver):
    headless, proxy_on, only_text = await get_hpo()

    #driver = await get_selenium_proxy(headless=headless, proxy=proxy_on)
    #driver.get(link)
    await asyncio.sleep(2)

    blocks = await blocks_pikabu(driver)

    print('Len', len(blocks))

    for block in blocks:
        date_content = block.find_element(By.CSS_SELECTOR, 'time[class="comment__datetime hint"]')
        date_full = date_content.get_attribute("datetime")
        if date_full in uniq_links:
            continue

        timestamp = datetime.strptime(date_full, '%Y-%m-%dT%H:%M:%S%z')
        date_ts = timestamp.timestamp()
        # Форматирование даты
        formatted_date = timestamp.strftime('%d.%m.%Y')

        parsed_datetime = timestamp.astimezone(None).replace(tzinfo=None)
        if (now - parsed_datetime) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней = {formatted_date}.')
            continue

        author = block.find_element(By.CSS_SELECTOR, 'span.user__nick').text
        try:
            feedback = block.find_element(By.CSS_SELECTOR, 'p.rv-comment').text
        except:
            continue

        await generate_and_white(service=service,
                                 url_answer=date_full,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)

async def main_alfa():
    headless, proxy_on, only_text = await get_hpo()
    service = await get_service()

    df = await read_table_id(service, ss_id, 'zoom')
    df_logs = await read_table_id(service, ss_id, 'logs')

    df_mini = df[["Проект", project]]
    #print(df_mini)

    df_mini_pattern = [row[project] for ind, row in df_mini.iterrows() if "Пример реакции" in row['Проект']]
    df_mini_criteria = [row[project] for ind, row in df_mini.iterrows() if "Особые критерии" in row['Проект']]

    links_alfa = df[project].tolist()
    #print(links_alfa)

    df_links = await read_table_id(service, ss_id, project)
    uniq_links = df_links['Link'].tolist()

    domens = {}

    for _url in links_alfa:
        if any(dom in _url for dom in ["google.com", "irecommend.ru", "otzovik.com", "sravni", "maps"]):
            continue

        domen = await get_domen(_url)
        if domen:
            domens[domen] = []

    for url_ in links_alfa:
        for k in domens.keys():
            if k in url_:
                domens[k].append(url_)
                break

    for k1, v1 in domens.items():
        print(f"{k1}: {len(v1)}")

    driver = await get_selenium_proxy(headless=headless, proxy=proxy_on)

    for key, value in domens.items():
        name_project = f"{project}_{key}"
        print(f"\n------------------{name_project}--------------------")
        start_time = time.time()

        filtered_logs = df_logs[df_logs['service_name'] == name_project]
        if not filtered_logs.empty:
            idx_logs = filtered_logs.index[0]

            # Пропуск по дате
            date_logs = df_logs.loc[idx_logs, 'date']
            if date_logs == current_date:
                continue

        for url in value:
            print(f'\n************{url}**************')

            if any(tm in url for tm in ['t.me', 'telegram.me']):
                continue

            elif "vk.com" in url:
                await check_vk(service, url, df_mini_pattern, df_mini_criteria, ss_id, project, uniq_links)

            elif 'youtube' in url:
                await check_youtube(service, url, df_mini_pattern, df_mini_criteria, ss_id, project, uniq_links)

            elif 'otvet.mail' in url:
                driver.get(url)
                await asyncio.sleep(5)
                try:
                    await check_otvet(service, url, df_mini_pattern, df_mini_criteria, ss_id, project, uniq_links)

                except Exception as Ex:
                    print(f'--- Ошибка функции Otvet {Ex}')

            elif any(tm in url for tm in ['dzen.ru', 'zen.yandex.ru']):
                driver.get(url)
                await asyncio.sleep(5)
                try:
                    driver = await check_dzen(service, url, df_mini_pattern, df_mini_criteria, ss_id, project, driver, uniq_links)
                except Exception as Ex:
                    print(f'--- Ошибка функции Dzen {Ex}')

            elif "pikabu.ru" in url:
                driver.get(url)
                await asyncio.sleep(5)
                try:
                    driver = await check_pikaby(service, url, df_mini_pattern, df_mini_criteria, ss_id, project, driver, uniq_links)
                except Exception as Ex:
                    print('--- Ошибка функции Dzen {Ex}')

            try:
                print(driver.title)

            except:
                print('- Driver quit!')
                print('-- New driver...')
                driver = await get_selenium_proxy(headless=headless, proxy=proxy_on)







        finish_sec = time.time() - start_time
        datas = {
            'service_name': name_project,
            'count': len(value),
            'date': current_date,
            'time': finish_sec}

        await write_log_sheet(service, ss_id, 'logs', datas)





    driver.close()
    driver.quit()





if "__main__" in __name__:
    asyncio.run(main_alfa())