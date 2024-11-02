import asyncio
import json
import os
import time

from datetime import datetime, timedelta
import random
from pprint import pprint

import pandas as pd
from bs4 import BeautifulSoup

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchWindowException
from selenium.webdriver.support.wait import WebDriverWait

from dotenv import load_dotenv
import re

from utils.central_module import wait_for_portal, get_local_ip, proxy_status, fix_error
from utils.constants import months, TABLES_LIST
from utils.ai_module import generate_and_white
from utils.gs_editor import get_service, pars_url, append_data_to_sheet_scope, get_table_scope, write_log_sheet, \
    append_data_to_sheet_cell
from utils.user_agent import get_selenium_proxy, extract_main_site

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

current_date = datetime.now()
record_date = current_date.strftime("%d.%m.%Y")
now_month = current_date.month

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))
timeout = 10000
ss_id = TABLES_LIST['zoom']
headless = True

async def cut_token(text, pattern):
    match = re.search(pattern, text)
    if match:
        result = match.group(1)
        print(result)
        return result


def find_key_path(dct, target_key, path = None):
    if path is None:
        path = []

    for k, v in dct.items():
        if k == target_key:
            path.append(k)
            return path

        elif isinstance(v, dict):
            result = find_key_path(v, target_key, path + [k])
            if result:
                return result

async def get_requestId(dictionary):
    if dictionary.get("stack"):
        reqId_1 = dictionary['stack'][0]
        if reqId_1.get('results'):
            reqId_2 = dictionary['stack'][0]['results']

            if reqId_2.get('requestId'):
                reqId = reqId_2['requestId']

            elif reqId_2.get('requestSerpId'):
                reqId = reqId_2['requestSerpId']

            elif reqId_2.get('items'):
                reqId_3 = reqId_2['items'][0]

                if reqId_3.get('requestId'):
                     reqId = reqId_3['requestId']

        elif reqId_1.get('response'):
            reqId_2 = dictionary['stack'][0]['response']

            if reqId_2.get('requestId'):
                reqId = reqId_2['requestId']

            elif reqId_2.get('items'):
                reqId_3 = reqId_2['items'][0]

                if reqId_3.get('requestId'):
                     reqId = reqId_3['requestId']

    print(reqId)
    return reqId

async def check_ya_new(driver, url):
    print("url:", url)
    domen = await extract_main_site(url)
    businessId = await get_id_org(url)
    top_url = f'{domen}/maps/org/{businessId}/reviews'
    print('top_url', top_url)

    driver.get(top_url)
    print(1)

    # Ждем некоторое время, чтобы AJAX-запросы успели выполниться
    driver.implicitly_wait(15)  # или другое подходящее время
    print(2)

    data_site = driver.find_element(By.CSS_SELECTOR, 'script.state-view')
    html_content = data_site.get_attribute("outerHTML")
    print(21)
    soup = BeautifulSoup(html_content, 'html.parser')
    script_tag = soup.find('script', {'class': 'state-view'})
    dictionary = json.loads(script_tag.string)
    print(22)
    reqId = await get_requestId(dictionary)
    sessionId = dictionary['config']['counters']['analytics']['sessionId']

    # Получаем логи производительности
    logs = driver.get_log('performance')
    #print(logs)
    print(3)
    url_s = None
    for idx, log in enumerate(logs):
        if '&s=' in str(log):
            print('**************')
            print(log)
            print('**************')

        if 'ajax' in str(log):
            print('-----------------------------------------')
            #pprint(log)
            print('-------------')
            msg = json.loads(log['message'])
            #pprint(msg)

            url_s = None
            if msg.get('message'):
                msg_m = msg['message']
                if msg_m.get('params'):
                    msg_p = msg_m['params']
                    if msg_p.get('headers'):
                        msg_h = msg_p['headers']
                        url_s = msg_h.get(":path", None)
                        break

                    elif msg_p.get('request'):
                        msg_h = msg_p['request']
                        url_s = msg_h.get("url", None)
                        break

                    elif msg_p.get('response'):
                        msg_h = msg_p['response']
                        url_s = msg_h.get("url", None)
                        break

    print('Url_s', url_s)
    if not url_s:
        return

    pattern = r"csrfToken=(.*?)&"
    csrfToken = await cut_token(str(url_s), pattern)

    pattern = r"&s=(.*?)&"
    s = await cut_token(str(url_s), pattern)

    # pattern = r"&sessionId=(.*?)"
    # sessionId = await cut_token(str(url_s), pattern)


    await asyncio.sleep(5)

    url = (f'{domen}/maps/api/business/fetchReviews?ajax=1&'
           f'businessId={businessId}&'
           f'csrfToken={csrfToken}&'
           f'locale=ru_US&'
           f'page=1&'
           f'pageSize=50&'
           f'ranking=by_time&'
           f'reqId={reqId}&'
           f's={s}&'
           f'sessionId={sessionId}')

    print(url)
    input('Wait...')

    driver.get(url)
    json_data = driver.page_source
    print(json_data)









            #
            #
            # s1 = msg['message']['params']['headers'][':path']
            # s2 = msg['message']['params']['request']['url']
            # s2 = msg['message']['params']['response']['url']






        # if 'csrfToken' in str(log):
        #     print('-----------------------------------------')
        #     print(log)
        #     pattern = r"csrfToken=(.*?)&"
        #     token = await cut_token(str(log), pattern)
        #     print(token)
        #     #return token
        #
        # if '&s=' in str(log):
        #     print('-----------------------------------------')
        #     print(log)
        #     pattern = r"&s=(.*?),"
        #     s = await cut_token(str(log), pattern)
        #     print(s)




    return None

async def check_ya(service, link, pattern, criteria, ss_id, project, driver):
    print(f'\nLink: {link}')

    driver.get(link)
    await wait_for_portal() #Время ожидания

    url = driver.current_url
    print("current url", url)

    id_org = await get_id_org(url)
    top_url = f'https://yandex.ru/maps/org/{id_org}/reviews'
    print('top_url', top_url)

    datas = {'project': project,
             'url': url,
             'top_url': top_url}

    await append_data_to_sheet_scope(service, ss_id, 'unique_url', datas)

    driver.get(top_url)
    print(f'Get: {top_url}')
    #driver.execute_script("document.body.style.zoom='0.5'")
    await asyncio.sleep(5)

    n = 0
    while True:
        try:
            rating_view = driver.find_element(By.CSS_SELECTOR, 'div.rating-ranking-view')
            rating_view.click()
            print('- Click 1')
            await asyncio.sleep(5)

            rating_ranking_view = driver.find_elements(By.CSS_SELECTOR, 'div[class="rating-ranking-view__popup-line"][role="button"]')
            rating_ranking_view[1].click()
            print('- Click 2')
            break

        except Exception as Ex:
            await asyncio.sleep(1)
            n += 1
            if n > 10:
                print(f'Error Ex, n = {n}: {Ex}')
                return

    logs = driver.get_log('performance')

    for idx, log in enumerate(logs):
        if 'fetchReviews' in str(log):
            print('**************')
            if log.get('message'):
                msg = json.loads(log['message'])
                #pprint(msg)

                if msg.get('message'):
                    msg_m = msg['message']
                    if msg_m.get('params'):
                        msg_p = msg_m['params']

                        if msg_p.get('headers'):
                            msg_h = msg_p['headers']
                            url_s = msg_h.get(":path", None)
                            break

                        elif msg_p.get('request'):
                            msg_h = msg_p['request']
                            url_s = msg_h.get("url", None)
                            break

                        elif msg_p.get('response'):
                            msg_h = msg_p['response']
                            url_s = msg_h.get("url", None)
                            break

            print('**************')

    domen = await extract_main_site(url)

    if domen not in url_s:
        url_api = domen + url_s
    else:
        url_api = url_s

    print("url_api", url_api)

    driver.get(url_api)
    await asyncio.sleep(3)

    # Парсим HTML-код страницы
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    try:
        json_text = soup.find('pre').text  # Извлекаем содержимое тега <pre>

    except Exception as Ex:
        print(f'Error Ex: {Ex}')
        await fix_error(service, project, link, str(soup))
        return

    # Конвертируем в словарь
    dictionary = json.loads(json_text)

    #print(dictionary)
    #print(type(dictionary))
    if dictionary.get('data'):
        if dictionary['data'].get('reviews'):
            reviews = dictionary['data']['reviews']
        else:
            return

    else:
        return

    len_r = len(reviews)
    print(f'Len_r: {len_r}')
    if len_r == 0:
        return None

    links = await pars_url(service, ss_id, project)

    for rew in reviews:
        if rew.get('text'):
            date_content = rew['updatedTime']
            date = datetime.strptime(date_content, "%Y-%m-%dT%H:%M:%S.%fZ")

            if (current_date - date) > timedelta(days=days_ago):
                print(f'--- Отзыв старше {days_ago} дней. = {date}')
                return 'Next...'

            author = rew['author']['name']
            #print(author)

            url_answer = rew['reviewId']
            #print(url_answer)
            if url_answer in links:
                print('Такой комментарий уже есть в списке')
                continue

            feedback = rew['text']
            #print(feedback)

            formatted_date = date.strftime("%d.%m.%Y")
            # print(formatted_date)

            await generate_and_white(service=service,
                                     url_answer=url_answer,
                                     author=author,
                                     formatted_date=formatted_date,
                                     ss_id=ss_id,
                                     project=project,
                                     feedback=feedback,
                                     pattern=pattern,
                                     criteria=criteria)

    return 'OK!'

async def get_id_org(url):
    url_split = url.split('/')
    for k, v in enumerate(url_split):
        if v.isdigit():
            return v

async def main_ya_maps():
    proxy_active = await proxy_status()
    print(f'Proxy status: {proxy_active}')

    driver = None
    if proxy_active == 'Active':
        driver = await get_selenium_proxy(headless=headless)

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

    for project in list_:
        if 'Проект' in project:
            continue

        #Если дата не совпадает с сегодняшней
        host_logs = ''

        project_ya_maps = f'{project}_ya_maps'
        filtered_logs = df_logs[df_logs['service_name'] == project_ya_maps]
        if not filtered_logs.empty:
            idx_logs = filtered_logs.index[0]

            if proxy_active != 'Active':
                await append_data_to_sheet_cell(service, ss_id, 'logs', 'proxy_status', idx_logs + 2, f'Proxy {proxy_active}')
                break

            else:
                await append_data_to_sheet_cell(service, ss_id, 'logs', 'proxy_status', idx_logs + 2,
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
        irec_link = [i for i in df_link_list if 'maps' in i]
        len_irec = len(irec_link)
        print(f'\n\n{project} Ya_maps link = {len_irec}')

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

            if 'maps' in link:
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

                status = await check_ya(service=service,
                                       link=link,
                                       pattern=df_mini_pattern,
                                       criteria=df_mini_criteria,
                                       ss_id=ss_id,
                                       project=project,
                                       driver=driver)

                if not status:
                    driver.quit()
                    driver = await get_selenium_proxy(headless=headless)

        if record:
            finish_sec = time.time() - start_time
            datas = {'service_name': project_ya_maps,
                    'count': len_irec,
                    'date': record_date,
                    'time': finish_sec}

            print('datas', datas)
            await write_log_sheet(service, ss_id, 'logs', datas)

    if driver:
        driver.close()

async def main():
    service = await get_service()

    url = 'https://yandex.ru/maps/org/artstudio_moskovsky/125846534919/?ll=30.329628%2C59.907103&mode=search&sll=30.301828%2C59.912472&sspn=0.022573%2C0.006756&text=Artstudio%20Moskovsky&z=14.86'
    #url = 'https://yandex.ru/maps/org/124956693444/reviews'
    #url = 'https://yandex.kz/maps/org/schastye/187776871438/reviews/?ll=66.272509%2C56.632288&utm_source=review&z=16'
    #url = 'https://yandex.kz/maps/org/krylya/115857625887/reviews/?ll=65.263154%2C57.147658&utm_source=review&z=16'

    driver = await get_selenium_proxy(headless=headless)
    await check_ya(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", 1, driver)



if __name__ == '__main__':
    asyncio.run(main_ya_maps())



# async def check_ya_old(service, url, pattern, criteria, ss_id, project, playwright, browser, page):
#     links = await pars_url(service, ss_id, project)
#
#     if not page:
#         # await browser.close()
#         # await playwright.stop()
#         return 'Сайт не отдал данные.'
#
#     url = page.url
#
#     id_org = await get_id_org(url)
#
#     top_url = f'https://yandex.ru/maps/org/{id_org}'
#
#     datas = {'project': project,
#              'url': url,
#              'top_url': top_url}
#
#     await append_data_to_sheet_scope(service, ss_id, 'unique_url', datas)
#
#     print(f"New link = {url}")
#
#     await page.goto(top_url + '/reviews')
#     await page.evaluate("document.body.style.zoom=0.5")
#
#     print('=> Rating By date')
#
#     for n in range(12):
#         if n == 10:
#             await browser.close()
#             await playwright.stop()
#             return 'Сайт не отдал данные'
#
#         try:
#             #button_default = await page.query_selector('div[class="rating-ranking-view"]')
#             button_default = await page.wait_for_selector('div[class="rating-ranking-view"]', timeout=timeout)
#             await button_default.click()
#             #await asyncio.sleep(1)
#             print('Click role...')
#
#             #button_new = await page.query_selector('div[class="rating-ranking-view__popup-line"][aria-label="По новизне"]')
#             button_new = await page.wait_for_selector('div[class="rating-ranking-view__popup-line"][role="button"]', timeout=timeout)
#             print(1)
#             button_new = await page.query_selector_all('div[class="rating-ranking-view__popup-line"][role="button"]')
#             print(len(button_new))
#             print(2)
#             await button_new[1].click()
#             print(3)
#             #await asyncio.sleep(3)
#             break
#
#         except Exception as Ex:
#             print(f"Попытка не удалась: {Ex}")
#             if n == 5:  # Если не последняя попытка
#                 await page.reload()  # Перезагрузить страницу
#
#             elif n == 10:
#                 await browser.close()
#                 await playwright.stop()
#                 return 'Не удалось нажать на кнопку.'  # Вернуть ошибку
#
#     print('=> Get blocks')
#
#     blocks = await page.query_selector_all('div[class="business-reviews-card-view__review"]')
#     print('Len ', len(blocks))
#
#     if len(blocks) == 0:
#         await browser.close()
#         await playwright.stop()
#         return
#
#     for block in blocks:
#         try:
#             date_element = await block.query_selector('meta[itemprop="datePublished"]')  # Corrected selector (should be 'meta')
#             date_content = await date_element.get_attribute('content')
#             date = datetime.strptime(date_content, "%Y-%m-%dT%H:%M:%S.%fZ")
#
#         except AttributeError as AE:
#             print(f'AE: {AE}')
#             date_element = await block.query_selector('span[class="business-review-view__date"]')
#             date = await date_element.inner_text()
#             print('Date =', date)
#
#             date_split = date.split(' ')
#             print("date_split", date_split)
#
#             if len(date_split) == 2:
#                 month_str = date_split[1]
#
#             elif len(date_split) == 3:
#                 month_str = date_split[1]
#                 year_str = date_split[2]
#
#                 if int(year_str) != current_date.year:
#                     print('Next year >>>')
#                     continue
#
#             month = await months(month_str)
#
#             if now_month != month:
#                 print('Next month >>>')
#                 continue
#
#             else:
#                 day = int(date_split[0])
#                 year = current_date.year
#                 date = datetime(year, month, day)
#
#             print("date =", date)
#
#         if (current_date - date) > timedelta(days=days_ago):
#             print(f'--- Отзыв старше {days_ago} дней. = {date}')
#             break
#
#         org_answer = await block.query_selector('div[class="business-review-view__comment-expand"]')
#         if org_answer:
#             print('Есть ответ представителя компании')
#             continue
#         else:
#             print('Ответа нет!')
#
#         for n in range(12):
#             if n == 10:
#                 await browser.close()
#                 await playwright.stop()
#                 return 'Сайт не предоставил данные'
#
#             try:
#                 #button_share = await block.query_selector('span[class="inline-image _loaded icon"]')
#                 #button_share = await block.query_selector('div[class="business-review-view__share-control"]')
#                 button_share = await page.wait_for_selector('div[class="business-review-view__share-control"]', timeout=5000)
#                 print('-> Click share')
#                 await button_share.click()
#                 print('-> Click share - OK!')
#                 await asyncio.sleep(3)
#                 break
#
#             except:
#                 await asyncio.sleep(2)
#
#         button_open = await page.query_selector('input[class="input__control"]')
#         url_answer = await button_open.get_attribute('value')
#         #print(url_answer)
#
#         await page.keyboard.press('Escape')
#
#         if url_answer in links:
#             print('Такой комментарий уже есть в списке')
#             continue
#
#         author_text = await block.query_selector('span[itemprop="name"]')
#         author = await author_text.inner_text()
#         #print(author)
#
#         feedback_text =  await block.query_selector('span[class="business-review-view__body-text"]')
#         feedback = await feedback_text.inner_text()
#         #print(feedback)
#
#         formatted_date = date.strftime("%d.%m.%Y")
#         #print(formatted_date)
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
# async def check_ya_old2(service, url, pattern, criteria, ss_id, project, playwright, browser, page):
#     links = await pars_url(service, ss_id, project)
#
#     if not page:
#         return 'Сайт не отдал данные.'
#
#     url = page.url
#
#     id_org = await get_id_org(url)
#
#     top_url = f'https://yandex.ru/maps/org/{id_org}'
#
#     datas = {'project': project,
#              'url': url,
#              'top_url': top_url}
#
#     await append_data_to_sheet_scope(service, ss_id, 'unique_url', datas)
#
#     print(f"New link = {url}")
#     await page.goto(top_url + '/reviews')
#     await page.evaluate("document.body.style.zoom=0.5")
#
#     #await page.wait_for_selector('script[class="state-view"]', timeout=timeout)
#     data_site_content = await page.query_selector('script[class="state-view"]')
#     data_site = await data_site_content.inner_text()
#
#     dictionary = json.loads(data_site)
#     #pprint(dictionary)
#
#     if dictionary['stack'][0].get("results"):
#         reviews = dictionary['stack'][0]['results']['items'][0]['reviewResults']['reviews']
#
#     elif dictionary['stack'][0].get("response"):
#         reviews = dictionary['stack'][0]['response']['items'][0]['reviewResults']['reviews']
#
#     else:
#         reviews = []
#
#     len_r = len(reviews)
#
#     if len_r == 0:
#         await browser.close()
#         await playwright.stop()
#         return
#
#     for rew in reviews:
#         #pprint(rew)
#         if rew.get('text'):
#             date_content = rew['updatedTime']
#             date = datetime.strptime(date_content, "%Y-%m-%dT%H:%M:%S.%fZ")
#             if (current_date - date) > timedelta(days=days_ago):
#                 print(f'--- Отзыв старше {days_ago} дней. = {date}')
#                 continue
#
#             author = rew['author']['name']
#             #print(author)
#
#             url_answer = rew['reviewId']
#             #print(url_answer)
#             if url_answer in links:
#                 print('Такой комментарий уже есть в списке')
#                 continue
#
#             feedback = rew['text']
#             print(feedback)
#
#             formatted_date = date.strftime("%d.%m.%Y")
#             # print(formatted_date)
#
#             await generate_and_white(service=service,
#                                      url_answer=url_answer,
#                                      author=author,
#                                      formatted_date=formatted_date,
#                                      ss_id=ss_id,
#                                      project=project,
#                                      feedback=feedback,
#                                      pattern=pattern,
#                                      criteria=criteria)
#     #
#     await browser.close()
#     await playwright.stop()
#     #
#     #
#     #
#     #
#     #
#     # print('**************************************************')
#     # businessId = id_org
#     # csrfToken = dictionary['config']['csrfToken']
#     # print(csrfToken)
#     #
#     # print('----------------------------------')
#     #
#     # reqId = await get_requestId(dictionary)
#     # print(reqId)
#     #
#     # sessionId = dictionary['config']['counters']['analytics']['sessionId']
#     # print(sessionId)
#     #
#     # url = (f'https://yandex.kz/maps/api/business/fetchReviews?ajax=1'
#     #        f'&businessId={businessId}'
#     #        f'&csrfToken={csrfToken}'
#     #        f'&locale=ru_KZ'
#     #        f'&page=1'
#     #        f'&pageSize=50'
#     #        f'&ranking=by_time'
#     #        f'&reqId={reqId}'
#     #        f'&s=2862124894'
#     #        f'&sessionId={sessionId}')
#     #
#     # print(url)
#     # r = requests.get(url)
#     # print(r)
#     #
#     # print(r.json())
#     #

#
# async def check_ya(service, link, pattern, criteria, ss_id, project, driver):
#     print(f'\nLink: {link}')
#
#     driver.get(link)
#     await wait_for_portal() #Время ожидания
#
#     url = driver.current_url
#     print("current url", url)
#
#     id_org = await get_id_org(url)
#     top_url = f'https://yandex.ru/maps/org/{id_org}/reviews'
#     print('top_url', top_url)
#
#     datas = {'project': project,
#              'url': url,
#              'top_url': top_url}
#
#     await append_data_to_sheet_scope(service, ss_id, 'unique_url', datas)
#
#     driver.get(top_url)
#     driver.execute_script("document.body.style.zoom='0.5'")
#     await asyncio.sleep(3)
#
#     #await page.wait_for_selector('script[class="state-view"]', timeout=timeout)
#     #data_site_content = await page.query_selector('script[class="state-view"]')
#     #data_site = await data_site_content.inner_text()
#
#     try:
#         data_site = driver.find_element(By.CSS_SELECTOR, 'script.state-view')
#         html_content = data_site.get_attribute("outerHTML")
#
#         soup = BeautifulSoup(html_content, 'html.parser')
#         script_tag = soup.find('script', {'class': 'state-view'})
#         dictionary = json.loads(script_tag.string)
#
#         if dictionary['stack'][0].get("results"):
#             reviews = dictionary['stack'][0]['results']['items'][0]['reviewResults']['reviews']
#
#         elif dictionary['stack'][0].get("response"):
#             reviews = dictionary['stack'][0]['response']['items'][0]['reviewResults']['reviews']
#
#         else:
#             reviews = []
#
#     except selenium.common.NoSuchElementException as NSEE:
#         print(f"Error NSEE: {NSEE}")
#         return None
#
#     len_r = len(reviews)
#
#     if len_r == 0:
#         return None
#
#     links = await pars_url(service, ss_id, project)
#
#     for rew in reviews:
#         #pprint(rew)
#         if rew.get('text'):
#             date_content = rew['updatedTime']
#             date = datetime.strptime(date_content, "%Y-%m-%dT%H:%M:%S.%fZ")
#
#             if (current_date - date) > timedelta(days=days_ago):
#                 print(f'--- Отзыв старше {days_ago} дней. = {date}')
#                 continue
#
#             author = rew['author']['name']
#             #print(author)
#
#             url_answer = rew['reviewId']
#             #print(url_answer)
#             if url_answer in links:
#                 print('Такой комментарий уже есть в списке')
#                 continue
#
#             feedback = rew['text']
#             #print(feedback)
#
#             formatted_date = date.strftime("%d.%m.%Y")
#             # print(formatted_date)
#
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
#     return 'OK!'