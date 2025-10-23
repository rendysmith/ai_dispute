import json
import re
import time
from pprint import pprint

import asyncio

from urllib.parse import urlparse, parse_qs

#from selenium.webdriver.common.by import By
#from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from sqlalchemy import or_, func

from datetime import datetime, timedelta, timezone, date

from models.mdl_tables import OrgLink
from utils.central_module import get_local_ip, wait_for_portal, get_hpo
from utils.db_loader import get_and_lock_row, read_data_from_db_filter_limit_universal

from utils.gs_editor import pars_url, get_service, append_data_to_sheet_scope, read_table_id, \
    append_data_to_sheet_scopes, append_data_to_sheet_cell, append_data_to_sheet_cells
from utils.ai_module import generate_and_white
from utils.user_agent import get_soup, get_selenium_proxy, get_playwright

import os
from dotenv import load_dotenv

current_date = datetime.now(timezone.utc)
rec_data = current_date.strftime("%d.%m.%Y")

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

headless, proxy_on, only_text = asyncio.run(get_hpo())
headless = True

async def text_to_json(script_text, start_word):
    json_start = script_text.find(start_word)

    if json_start == -1:
        raise ValueError("Начало JSON не найдено")

    json_end = script_text.find('}', json_start + 1)

    while True:
        try:
            json_content = script_text[json_start:json_end]
            json_str = "{" + json_content + "}"  # Предварительный JSON словарь
            data_dict = json.loads(json_str)
            return data_dict

        except:
            json_end = script_text.find('}', json_end + 1)

async def get_id_key(driver, url):
    print('--- get key 1')
    async def get_query(url):
        #print(url)
        #print('-----------org_id-key-----------')
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        if query_params.get('key'):
            key = query_params['key'][0]
            #print(key)

        api_org_id = await get_id_obj(url)
        #print(api_org_id)

        return api_org_id, key

    driver.get(url)
    await asyncio.sleep(15)
    driver.execute_cdp_cmd("Network.enable", {})

    logs = driver.get_log('performance')
    for entry in logs:
        if all(i in str(entry) for i in ['key=', 'public-api']):
            print('\n--------------------------------\n')
            if entry.get('message'):
                flow = json.loads(entry['message'])
                #pprint(flow)
                if flow.get('message'):
                    if flow['message'].get('params'):
                        if flow['message']['params'].get('request') or flow['message']['params'].get('response'):
                            if flow['message']['params'].get('request'):
                                url = flow['message']['params']['request']['url']
                                print(url)
                                api_org_id, key = await get_query(url)
                                if api_org_id and key:
                                    return api_org_id, key

                            elif flow['message']['params'].get('response'):
                                url = flow['message']['params']['response']['url']
                                print(url)
                                api_org_id, key = await get_query(url)
                                if api_org_id and key:
                                    return api_org_id, key

                        elif flow['message']['params'].get('headers'):
                            if flow['message']['params']['headers'].get('path'):
                                url = flow['message']['params']['headers']['path']
                                print(url)
                                api_org_id, key = await get_query(url)
                                if api_org_id and key:
                                    return api_org_id, key

    return None, None

async def get_key(page_source: str):
    print('--- get key 2')
    # driver.get(url)
    # await asyncio.sleep(15)
    #
    # page_source = driver.page_source

    pattern = r'"reviewApiKey":"([^"]*)"'
    match = re.search(pattern, page_source)
    print("--- match:", match)
    try:
        key_id = match.group(1)
    except:
        print(page_source)

    org_content = await text_to_json(page_source, '"org":{"')
    api_org_id = org_content['org']['id']

    return api_org_id, key_id

async def get_driver():
    return await get_selenium_proxy(headless=headless, proxy=proxy_on)

async def data_empty():
    datas = {'Date': [],
             'Feedback':[],
             'Link':[],
             'Author': [],
             'Rating': []}

    return datas

async def get_id_obj(url):
    url_split = url.split('/')
    #city_company = url_split[3]

    id_obj = ''
    for idx, v in enumerate(url_split):
        if v == 'firm':
            id_obj = url_split[idx + 1]
            break

        elif v == 'orgs':
            id_obj = url_split[idx + 1]
            break

        elif v == 'geo':
            id_obj = url_split[idx + 1]
            break

        elif v == "reviews":
            id_obj = url_split[idx + 1]
            break

    return id_obj.strip()

async def blocks_2gis_sel(driver, url):
    top_url = url + '/tab/reviews'
    print(top_url)
    driver.get(top_url)

    await wait_for_portal() #Время ожидания

    script_element = driver.find_element(By.XPATH, "//script[contains(., 'var __customcfg')]")
    script_text = script_element.get_attribute("innerHTML")
    #print(script_text)
    data_dict = await pars_json_data(script_text)

    if not data_dict:
        return {}

    if not isinstance(data_dict, dict):
        return {}

    return data_dict['review']

async def blocks_2gis_bs4(org_id, key):
    api_url = f'https://public-api.reviews.2gis.com/3.0/orgs/{org_id}/reviews?limit=50&fields=meta.org_rating,meta.org_reviews_count,meta.total_count,reviews.object.address,reviews.hiding_reason&without_my_first_review=false&rated=true&sort_by=date_created&key={key}&locale=ru_RU'
    print("ApiKeyURL: ", api_url)

    r_json = await get_soup(api_url, only_text=False, proxy=proxy_on)

    blocks = r_json['reviews']
    org_rating = r_json['meta']['org_rating']
    org_reviews_count = r_json['meta']['org_reviews_count']

    print(f'Len_B = {len(blocks)}')
    return blocks, org_rating, org_reviews_count

async def send_top_url(service, ss_id, project, url):
    id_obj = await get_id_obj(url)
    top_url = f'https://2gis.ru/firm/{id_obj}'
    print(top_url)

    datas = {'project': project,
             'url': url,
             'top_url': top_url}

    await append_data_to_sheet_scope(service, ss_id, 'unique_url', datas)
    await asyncio.sleep(3)
    return id_obj, top_url

async def soup_pars(service, url, links, pattern, criteria, ss_id, project, zoom=True):
    try:
        blocks, branch_rating, branch_reviews_count = await blocks_2gis_bs4(url, key)
    except:
        return

    datas = await data_empty()

    for block in blocks:
        if zoom:
            official_answer = block['official_answer']
            if not official_answer and zoom:
                print("Уже есть ответ компании.")
                continue

        date_content = block['date_created']
        date = datetime.strptime(date_content, "%Y-%m-%dT%H:%M:%S.%f%z")

        if zoom:
            if (current_date - date) > timedelta(days=days_ago):
                print(f'--- Отзыв старше {days_ago} дней. = {date}')
                return
        else:
            if (current_date - date) > timedelta(days=35):
                print(f'--- Отзыв старше 35 дней. = {date}')
                return

        url_answer = block['id']
        if url_answer in links:
            print('- Такой комментарий уже есть в списке')
            continue

        formatted_date = date.strftime("%d.%m.%Y")

        feedback = block['text']

        author_content = block['user']['name']
        author = f"{author_content}\n{url}"

        rating = block['rating']

        if zoom:
            await generate_and_white(service=service,
                                     url_answer=url_answer,
                                     author=author,
                                     formatted_date=formatted_date,
                                     ss_id=ss_id,
                                     project=project,
                                     feedback=feedback,
                                     pattern=pattern,
                                     criteria=criteria)

        else:
            datas['Date'].append(formatted_date)
            datas['Feedback'].append(feedback)
            datas['Link'].append(url_answer)
            datas['Author'].append(author_content)
            datas['Rating'].append(rating)

    if zoom == False:
        await append_data_to_sheet_scopes(service, ss_id, '2gis', datas)
        await asyncio.sleep(3)

async def pars_json_data(script_text):
    json_start = script_text.find('"review":{')

    if json_start == -1:
        raise ValueError("Начало JSON не найдено")

    json_end = script_text.find('}', json_start + 1)

    while True:
        try:
            json_content = script_text[json_start:json_end]
            json_str = "{" + json_content + "}"  # Предварительный JSON словарь
            data_dict = json.loads(json_str)
            return data_dict

        except:
            json_end = script_text.find('}', json_end + 1)

async def play_pars(service, page, links, top_url, pattern, criteria, ss_id, project, id_org, row, zoom=True):
    org_id = row['org_id']
    key = row['key']
    key_idx = row.name
    print(key_idx + 2, org_id, key)

    if org_id == None or key == None or org_id == "" or key == "":
        full_url = top_url + "/tab/reviews"

        try:
            await page.goto(full_url)
        except Exception as ex:
            print(f'-Error Playwrigh: {ex}')
            return
        #await asyncio.sleep(5000)
        await page.wait_for_timeout(5000)

        page_content = await page.content()
        org_id, key = await get_key(page_content)

        # if org_id == None or key == None:
        #     org_id, key = await get_id_key(driver, full_url)

        if org_id == None or key == None:
            return int(time.time())

        await append_data_to_sheet_cells(service, '1k00OxnK8MekEVu2dmL2IqT1uxTQxWEzd0Aur5a8ILEE', '2gis', ['org_id', 'key'], key_idx + 2, [org_id, key])
        await asyncio.sleep(3)
        
    blocks, org_rating, org_reviews_count = await blocks_2gis_bs4(org_id, key)
    if len(blocks) == 0:
        print('Len B = 0')
        return org_id

    datas = await data_empty()

    for k, block in enumerate(blocks):
        date_content = block['date_created']
        date = datetime.strptime(date_content, "%Y-%m-%dT%H:%M:%S.%f%z")

        if zoom:
            if (current_date - date) > timedelta(days=days_ago):
                print(f'--- Отзыв старше {days_ago} дней. = {date}')
                return org_id

            official_answer = block['data']['official_answer']
            if not official_answer:
                print("Уже есть ответ компании.")
                continue

        else:
            if (current_date - date) > timedelta(days=days_ago):
                print(f'--- Отзыв старше {days_ago} дней. = {date}')
                return org_id

        user_id = block['id']
        url_answer = f'https://2gis.ru/firm/{id_org}/tab/reviews/review/{user_id}'

        if url_answer in links:
            print('Такой комментарий уже есть в списке')
            continue

        formatted_date = date.strftime("%d.%m.%Y")

        feedback = block['text']
        author = block['user']['name']
        rating = block['rating']

        if zoom:
            await generate_and_white(service=service,
                                     url_answer=url_answer,
                                     author=author,
                                     formatted_date=formatted_date,
                                     ss_id=ss_id,
                                     project=project,
                                     feedback=feedback,
                                     pattern=pattern,
                                     criteria=criteria)

        else:
            datas['Date'].append(formatted_date)
            datas['Feedback'].append(feedback)
            datas['Link'].append(url_answer)
            datas['Author'].append(author)
            datas['Rating'].append(rating)

    if zoom == False:
        await append_data_to_sheet_scopes(service, ss_id, '2gis', datas)
        await asyncio.sleep(3)

    return org_id

async def check_2gis(service, url, pattern, criteria, ss_id, project, links=False, zoom=True):
    if not links:
        links = await pars_url(service, ss_id, project)

    id_org, top_url = await send_top_url(service, ss_id, project, url)

    if any(fo in url for fo in ['firm', 'orgs']):
        await soup_pars(service, url, links, pattern, criteria, ss_id, project, zoom)

    elif 'geo' in url:
        await play_pars(service, links, top_url, pattern, criteria, ss_id, project, id_org, zoom)

async def main_2gis_sberstrem_old():


    service = await get_service()
    datas_ss_id = '1k00OxnK8MekEVu2dmL2IqT1uxTQxWEzd0Aur5a8ILEE'
    zoom_ss_id = "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w"
    project = '2gis'

    local_ip = await get_local_ip()
    print("- local_ip", local_ip)
    if '176.124' in local_ip:
        local_data = {'host': local_ip}
        await append_data_to_sheet_scope(service, datas_ss_id, 'hosts', local_data)
        await asyncio.sleep(3)

    print('************DF***************')
    df_links = await read_table_id(service, datas_ss_id, project)
    df_links = df_links[(df_links['host'] == local_ip) & (df_links['date'] != rec_data)]

    if df_links.empty:
        print("Df Len:", len(df_links))
        return

    print(df_links)

    links = await pars_url(service, zoom_ss_id, project)

    #driver = await get_driver()
    browser, context, page = await get_playwright()

    org_ids = []

    for k, row in df_links.iterrows():
        link = row['link']
        print(f'\n-------------------------------------\n{link}')

        org_id = row['org_id']
        if org_id in org_ids:
            print('Next...', org_id, org_ids)
            await append_data_to_sheet_cells(service,
                                             datas_ss_id,
                                             '2gis',
                                             ['date', 'time'],
                                             k + 2,
                                             [rec_data, -1])
            await asyncio.sleep(3)
            continue

        date = row['date']

        if date == rec_data:
            print('date == rec_data')
            continue

        org_id = await rec_datas(page, row, links)
        org_ids.append(org_id)

        if k // 10 == 0:
            links = await pars_url(service, zoom_ss_id, project)

    await browser.close()

 async def rec_datas(page, row, links):
        link = row['link']

        start_time = time.time()

        id_obj = await get_id_obj(link)
        top_url = f'https://2gis.ru/firm/{id_obj}'

        org_id = await play_pars(service, page, links, top_url, 1, 1, zoom_ss_id, project, id_obj, row, zoom=False)

        total_time = int(time.time() - start_time)
        await append_data_to_sheet_cells(service, datas_ss_id, '2gis', ['date', 'time'], k + 2, [rec_data, total_time])
        await asyncio.sleep(3)

        return org_id

async def main_2gis_sberstrem():
    browser, context, page = await get_playwright()

    today = date.today()
    print(today)
    filter = func.date(OrgLink.date) != today
    status, result  = await read_data_from_db_filter_limit_universal('org_links', 5000, 1, filters=filter)

    if not status:
        return

    # for r in result[:5]:
    #     print(r.link_id, r.date)

    len_r = len(result)
    print(len_r)


    filters = or_(
        OrgLink.date.is_(None),
        func.date(OrgLink.date) != today
    )

    for i in range(3):
        row = await get_and_lock_row(OrgLink, filters)
        org_id = await rec_datas(page, row, links)

        print(row.link_id, row.date, )











    #await browser.close()


if __name__ == '__main__':
    #driver = asyncio.run(get_driver())
    #url = 'https://2gis.ru/yaroslavl/firm/70000001045733822/tab/reviews'

    # ord_id, key = asyncio.run(get_key(driver, url))
    # print('--------------------------------------------')
    # print(ord_id, key)

    # org_id, key = asyncio.run(get_id_key(driver, url))
    # print('--------------------FINISH------------------------')
    # print(org_id, key)
    # input()

    asyncio.run(main_2gis_sberstrem())




