import json
import re
import time
from pprint import pprint

from urllib.parse import urlparse, parse_qs

import asyncio
import random

from selenium.webdriver.common.by import By

from datetime import datetime, timedelta, timezone

from utils.central_module import get_local_ip, wait_for_portal, get_hpo
from utils.compressor import compress_string
from utils.gs_editor import pars_url, get_service, append_data_to_sheet_scope, read_table_id, \
    append_data_to_sheet_scopes, append_data_to_sheet_cell, append_data_to_sheet_cells
from utils.ai_module import generate_and_white
from utils.user_agent import get_soup, get_selenium_proxy

from utils.constants import months

import os
from dotenv import load_dotenv

current_date = datetime.now(timezone.utc)
rec_data = current_date.strftime("%d.%m.%Y")

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

async def get_key(driver, url):
    print(f'*******************{url}*********************')
    driver.get(url)
    await asyncio.sleep(5)

    logs = driver.get_log('performance')
    for obj in logs:
        if 'key=' in str(obj):
            print(obj)
            js = json.loads(obj['message'])
            if js['message']['params'].get('request'):
                url = js['message']['params']['request']['url']
                parsed_url = urlparse(url)
                print("\n--------------parsed_url------------------\n", parsed_url)

                path = parsed_url.path
                print(path)
                api_org_id = await get_id_obj(path)
                print(api_org_id)

                query_params = parse_qs(parsed_url.query)
                print("\n--------------query_params------------------\n", query_params)
                key = query_params['key'][0]
                print('****************************************')
                return api_org_id, key

async def get_driver():
    return await get_selenium_proxy(headless=True, proxy=False)

async def data_empty():
    datas = {'Date': [],
             'Feedback':[],
             'Link':[],
             'Author': [],
             'Rating': []}

    return datas

async def get_id_obj(url):
    url_split = url.split('/')
    print("url_split", url_split)
    #city_company = url_split[3]

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

async def blocks_2gis_bs4(url, org_id, key):
    #id_obj = await get_id_obj(url)

    #api_url = f'https://public-api.reviews.2gis.com/2.0/branches/{id_obj}/reviews?limit=50&is_advertiser=true&fields=meta.providers,meta.branch_rating,meta.branch_reviews_count,meta.total_count,reviews.hiding_reason,reviews.is_verified&without_my_first_review=false&rated=true&sort_by=date_created&key=b0209295-ae15-48b2-acb2-58309b333c37&locale=ru_RU'
    #api_url = f'https://public-api.reviews.2gis.com/3.0/orgs/{id_obj}/reviews?limit=50&fields=meta.org_rating,meta.org_reviews_count,meta.total_count,reviews.object.address,reviews.hiding_reason&without_my_first_review=false&rated=true&sort_by=date_created&key=6e7e1929-4ea9-4a5d-8c05-d601860389bd&locale=ru_RU'
    #api_url = f'https://public-api.reviews.2gis.com/3.0/orgs/{id_obj}/reviews?limit=50&fields=meta.org_rating,meta.org_reviews_count,meta.total_count,reviews.object.address,reviews.hiding_reason&without_my_first_review=false&rated=true&sort_by=date_created&key=6e7e1929-4ea9-4a5d-8c05-d601860389bd&locale=ru_RU'
    api_url = f'https://public-api.reviews.2gis.com/3.0/orgs/{org_id}/reviews?limit=50&fields=meta.org_rating,meta.org_reviews_count,meta.total_count,reviews.object.address,reviews.hiding_reason&without_my_first_review=false&rated=true&sort_by=date_created&key={key}&locale=ru_RU'
    print(api_url)

    headless, proxy_on, only_text = await get_hpo()
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

async def pars_json_data(script_text):
    #print(script_text)
    json_start = script_text.find('"review":{')
    #print(json_start)
    if json_start == -1:
        raise ValueError("Начало JSON не найдено")

    #print(json_start)
    #print(script_text[json_start:json_start+10])

    json_end = script_text.find('}', json_start + 1)

    while True:
        try:
            json_content = script_text[json_start:json_end]
            json_str = "{" + json_content + "}"  # Предварительный JSON словарь
            data_dict = json.loads(json_str)
            return data_dict

        except:
            json_end = script_text.find('}', json_end + 1)
            #print(f'--{json_end}--')

async def selen_pars(service, driver, links, top_url, pattern, criteria, ss_id, project, id_org, row, zoom=True):
    print(row)
    org_id = row['org_id']
    key = row['key']
    key_idx = row.name

    if org_id == "" or key == "":
        full_url = top_url + "/tab/reviews"
        org_id, key = await get_key(driver, full_url)

        await append_data_to_sheet_cells(service, '1k00OxnK8MekEVu2dmL2IqT1uxTQxWEzd0Aur5a8ILEE', '2gis', ['org_id', 'key'], key_idx + 2, [org_id, key])

    blocks, org_rating, org_reviews_count = await blocks_2gis_bs4(top_url, org_id, row)

    datas = await data_empty()

    for k, block in blocks.items():
        date_content = block['data']['date_created']
        date = datetime.strptime(date_content, "%Y-%m-%dT%H:%M:%S.%f%z")

        if zoom:
            if (current_date - date) > timedelta(days=days_ago):
                print(f'--- Отзыв старше {days_ago} дней. = {date}')
                continue

            official_answer = block['data']['official_answer']
            if not official_answer:
                print("Уже есть ответ компании.")
                continue

        else:
            if (current_date - date) > timedelta(days=40):
                print(f'--- Отзыв старше 40 дней. = {date}')
                continue

        user_id = block['data']['id']
        url_answer = f'https://2gis.ru/firm/{id_org}/tab/reviews/review/{user_id}'

        if url_answer in links:
            print('Такой комментарий уже есть в списке')
            continue

        formatted_date = date.strftime("%d.%m.%Y")

        feedback = block['data']['text']
        author = block['data']['user']['name']
        rating = block['data']['rating']

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

async def check_2gis(service, url, pattern, criteria, ss_id, project, links=False, zoom=True):
    if not links:
        links = await pars_url(service, ss_id, project)

    id_org, top_url = await send_top_url(service, ss_id, project, url)

    if any(fo in url for fo in ['firm', 'orgs']):
        await soup_pars(service, url, links, pattern, criteria, ss_id, project, zoom)

    elif 'geo' in url:
        await selen_pars(service, links, top_url, pattern, criteria, ss_id, project, id_org, zoom)

async def main_2gis_sberstrem():
    service = await get_service()
    datas_ss_id = '1k00OxnK8MekEVu2dmL2IqT1uxTQxWEzd0Aur5a8ILEE'
    zoom_ss_id = "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w"
    project = '2gis'

    local_ip = await get_local_ip()
    print(local_ip)
    if '176.124' in local_ip:
        local_data = {'host': local_ip}
        await append_data_to_sheet_scope(service, datas_ss_id, 'hosts', local_data)

    df_links = await read_table_id(service, datas_ss_id, project)
    df_links = df_links[df_links['host'] == local_ip]
    print(df_links)

    links = await pars_url(service, zoom_ss_id, project)

    driver = await get_driver()

    async def rec_datas(driver, row, links):
        link = row['link']

        start_time = time.time()

        id_obj = await get_id_obj(link)
        top_url = f'https://2gis.ru/firm/{id_obj}'

        await selen_pars(service, driver, links, top_url, 1, 1, zoom_ss_id, project, id_obj, row)

        total_time = int(time.time() - start_time)
        await append_data_to_sheet_cells(service, datas_ss_id, '2gis', ['date', 'time'], k + 2, [rec_data, total_time])

    for k, row in df_links.iterrows():
        link = row['link']
        print(f'\n----------------------------------------------------------\n{link}')

        if k // 10 == 0:
            links = await pars_url(service, zoom_ss_id, project)

        date = row['date']
        #time = row['time']

        if date == rec_data:
            return

        await rec_datas(driver, row, links)

    driver.quit()

if __name__ == '__main__':
    # driver = asyncio.run(get_driver())
    # url = 'https://2gis.ru/firm/70000001046153619/tab/reviews'
    #
    # key = asyncio.run(get_key(driver, url))
    # print('--------------------------------------------')
    # print(key)

    asyncio.run(main_2gis_sberstrem())




