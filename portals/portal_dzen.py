import json
from pprint import pprint

import asyncio
import os
import random

import requests

from datetime import datetime, timedelta
import time

from dotenv import load_dotenv

from selenium.webdriver.common.by import By

from utils.central_module import get_local_ip, get_hpo
from utils.gs_editor import get_service, get_table_scope, pars_url
from utils.ai_module import generate_and_white
from utils.user_agent import get_selenium_proxy, get_soup

current_date = datetime.now()

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

time_unix = str(time.time() * 1000)

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

# local_ip = asyncio.run(get_local_ip())
# if '176.124.192' in local_ip:
#     headless = True
#     proxy_on = True
#     only_text = False
#
# else:
#     print(f'local_ip Dzen: {local_ip}')
#     headless = False
#     proxy_on = False
#     only_text = False

async def blocks_dzen(driver):
    page_source = driver.page_source
    if 'Такой страницы не существует' in str(page_source):
        return [], []

    # driver = await get_selenium_proxy(url, headless=headless, proxy=proxy_on)
    # driver.get(url)

    zen_object_id = driver.find_element(By.CSS_SELECTOR, 'meta[property="zen_object_id"]').get_attribute('content').split(':')
    #print(zen_object_id)
    documentId = zen_object_id[1]
    publicationPublisherId = zen_object_id[0]

    url_json = f'https://dzen.ru/api/comments/v2/root-comments?documentId=native%3A{documentId}&publicationPublisherId={publicationPublisherId}'
    r = requests.get(url_json).json()
    len_r = len(r['items'])

    if len_r == 0:
        url_json = f'https://dzen.ru/api/comments/v2/root-comments?documentId=brief%3A{documentId}&publicationPublisherId={publicationPublisherId}'
        r = requests.get(url_json).json()
        len_r = len(r['items'])

    if len_r == 0:
        driver.quit()
        return [], []

    UsersByID = {v['uidSafe']: v['displayName'] for k, v in r['usersById'].items()}

    return r['items'], UsersByID

async def blocks_dzen_media(driver):
    comment_button = driver.find_elements(By.CSS_SELECTOR, 'button[class*="video-site--base-button"][type="button"][tabindex="0"]')
    print('comment_button 1:', len(comment_button))

    if len(comment_button) > 2:
        comment_button[2].click()
        print('--- Click comment 1...')

    if len(comment_button) == 0:
        comment_button = driver.find_elements(By.CSS_SELECTOR,
                                              'button[class*="shorts--base-button__rootElement-12"][type="button"][tabindex="0"]')

        print('comment_button 2:', len(comment_button))

    if len(comment_button) > 2:
        comment_button[2].click()
        print('--- Click comment 2...')

    await asyncio.sleep(3)

    logs = driver.get_log('performance')
    #print(logs)
    api_url = None
    for idx, log in enumerate(logs):
        if 'root-comments' in str(log):
            #pprint(log)

            if log.get('message'):
                msg = json.loads(log['message'])
                #pprint(msg)

                if msg.get('message'):
                    msg_msg = msg['message']

                    if msg_msg.get('params'):
                        msg_par = msg_msg['params']

                        if msg_par.get("request"):
                            msg_req = msg_par['request']

                            if msg_req.get('url'):
                                api_url = msg_req['url']

                        elif msg_par.get('response'):
                            msg_req = msg_par['response']

                            if msg_req.get('url'):
                                api_url = msg_req['url']

    if not api_url:
        return None

    headless, proxy_on, only_text = await get_hpo()
    r_json = await get_soup(api_url, only_text=False, proxy=proxy_on)

    blocks = r_json['items']
    UsersByID = {v['uidSafe']: v['displayName'] for k, v in r_json['usersById'].items()}

    return blocks, UsersByID

async def check_dzen(service, url, pattern, criteria, ss_id, project, driver):
    for i in range(3):
        try:
            not_robot_button = driver.find_element(By.CSS_SELECTOR, 'input[id="js-button"][class="CheckboxCaptcha-Button"]')
            not_robot_button.click()
            return

        except:
            await asyncio.sleep(3)

    #print(UsersByID)
    links = await pars_url(service, ss_id, project)

    if any(lk in url for lk in ['video', 'media', 'shorts']):
        blocks, UsersByID = await blocks_dzen_media(driver)

    else:
        blocks, UsersByID = await blocks_dzen(driver)

    if len(blocks) == 0:
        return

    for block in blocks:
        #print(block)
        url_answer = block['entityData']['id']
        #print(url_answer)

        if url_answer in links:
            print('Такой комментарий уже есть в списке')
            continue

        date = block['entityData']['createdTs']/1000
        #print(date)

        # Форматирование даты
        date_content = datetime.fromtimestamp(date)
        formatted_date = date_content.strftime('%d.%m.%Y')

        if (time.time() - date) > 7 * 24 * 3600:
            print(f'--- Отзыв старше 30 дней = {formatted_date}.')
            continue

        #date = datetime.fromtimestamp(timestamp_sec)

        #print(formatted_date)

        #authorSafeUid = block['authorSafeUid']
        author = UsersByID[block['entityData']['authorSafeUid']]
        #print(author)
        feedback = block['entityData']['text']

        await generate_and_white(service=service,
                                 url_answer=url_answer,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)

    driver.quit()



async def main_dzen():
    service = await get_service()
    url = 'https://dzen.ru/a/Y256lfZgtFWmCJ8F#comment_1391738222'

    headless, proxy_on, only_text = await get_hpo()
    driver = await get_selenium_proxy(url, headless=headless, proxy=proxy_on)
    await check_dzen(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", "AlphaPet", driver)

if __name__ == '__main__':
    asyncio.run(main_dzen())




#
# async def check_dzen_old(service, url, pattern, criteria, ss_id, project, playwright, browser, page):
#     #playwright, browser, page = await get_playwright(url)
#
#     links = await pars_url(service, ss_id, project)
#
#     if not page:
#         # await browser.close()
#         # await playwright.stop()
#         return 'Сайт не отдал данные.'
#
#     try:
#         zen_object_id_content = await page.query_selector('meta[property="zen_object_id"]')
#         zen_object_id = await zen_object_id_content.get_attribute('content')
#         zen_object_id = zen_object_id.split(':')
#
#     except:
#         await browser.close()
#         await playwright.stop()
#         return 'Сайт не отдал данные.'
#
#     #print(zen_object_id)
#     documentId = zen_object_id[1]
#     publicationPublisherId = zen_object_id[0]
#
#     url_json = f'https://dzen.ru/api/comments/v2/root-comments?documentId=native%3A{documentId}&publicationPublisherId={publicationPublisherId}'
#     r = requests.get(url_json).json()
#     len_r = len(r['items'])
#
#     if len_r == 0:
#         url_json = f'https://dzen.ru/api/comments/v2/root-comments?documentId=brief%3A{documentId}&publicationPublisherId={publicationPublisherId}'
#         r = requests.get(url_json).json()
#         len_r = len(r['items'])
#
#     print(len_r)
#     if len_r == 0:
#         await browser.close()
#         await playwright.stop()
#         return
#
#     UsersByID = {v['uidSafe']: v['displayName'] for k, v in r['usersById'].items()}
#     #print(UsersByID)
#
#     for block in r['items']:
#         #print(block)
#         url_answer = block['entityData']['id']
#         #print(url_answer)
#
#         if url_answer in links:
#             print('Такой комментарий уже есть в списке')
#             continue
#
#         date = block['entityData']['createdTs']/1000
#         print(date)
#
#         if (time.time() - date) > 7 * 24 * 3600:
#             print(f'--- Отзыв старше 30 дней = {date}.')
#             continue
#
#         # Форматирование даты
#         #formatted_date = date.strftime('%d.%m.%Y')
#         formatted_date = datetime.fromtimestamp(date).strftime('%d.%m.%Y')
#
#         #authorSafeUid = block['authorSafeUid']
#         author = UsersByID[block['entityData']['authorSafeUid']]
#         #print(author)
#
#         feedback = block['entityData']['text']
#         #input(feedback)
#
#         await generate_and_white(service=service,
#                                  url_answer=url_answer,
#                                  author=author,
#                                  formatted_date=formatted_date,
#                                  ss_id=ss_id,
#                                  project=project,
#                                  feedback=feedback,
#                                  pattern=pattern,
#                                  criteria=criteria)
#
#     await browser.close()
#     await playwright.stop()
