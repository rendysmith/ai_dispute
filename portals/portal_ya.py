import asyncio
import random
import os

import requests

from datetime import datetime, timedelta
import time

from pprint import pprint
from selenium.webdriver.common.by import By

from utils.gs_editor import get_service, get_table_scope, pars_url
from utils.ai_module import generate_and_white
from utils.user_agent import gen_ua, get_selenium, get_playwright

from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

current_date = datetime.now()
now_month = current_date.month

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

async def convert_date(month):
    months = {
        'января': 1,
        'февраля': 2,
        "марта": 3,
        "апреля": 4,
        "мая": 5,
        "июня": 6,
        "июля": 7,
        "августа": 8,
        "сентября": 9,
        "октября": 10,
        "ноября": 11,
        "декабря": 12
    }
    return months[month]

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

async def check_ya_sel(service, url, pattern, criteria, ss_id, project):
    links = await pars_url(service, ss_id, project)
    ts = random.randint(5, 6)
    print(f'Wait {ts} sec...')
    await asyncio.sleep(ts)

    driver = await get_selenium(url, headless=False)
    driver.get(url)
    driver.execute_script("document.body.style.zoom='50%'")

    n = 0
    while n < 10:
        try:
            button_reviev = driver.find_element(By.CSS_SELECTOR, 'div[class="tabs-select-view__title _name_reviews"]')
            button_reviev.click()
            await asyncio.sleep(5)
            break

        except:
            print('Error Click Review')
            await asyncio.sleep(5)
            n += 1

    # Получение сетевых логов
    n = 0
    while n < 5:
        logs = driver.get_log('performance')
        print(len(logs))
        for log in logs:
            if 'fetchReviews' in str(log):
                pprint(log)

                path_path = find_key_path(log, 'path')
                print(path_path)
                path_url = find_key_path(log, 'url')
                print(path_url)

                input('wait....')
        time.sleep(5)
        n += 1





    input('Wait...')










    url = "https://yandex.ru/maps/api/business/fetchReviews?ajax=1&businessId=149979773456&csrfToken=57bc959376278aec39d19dae3c62f6b5638229a3%3A1723636953&locale=ru_RU&page=1&pageSize=50&ranking=by_time&reqId=1723636953293713-3174470668-addrs-upper-yp-13&s=1603452967&sessionId=1723636953246801-9621007603936156238-balancer-l7leveler-kubr-yp-vla-144-BAL"

    headers = await gen_ua('https://yandex.ru')
    r = requests.get(url, headers=headers).json()
    print(r)
    print(list(r))
    input(len(r))





















    while True:
        try:
            review_button = driver.find_element(By.CSS_SELECTOR, 'div[class="tabs-select-view__title _name_reviews"]')
            review_button.click()
            break

        except:
            await asyncio.sleep(3)

    input()

















    zen_object_id = driver.find_element(By.CSS_SELECTOR, 'meta[property="zen_object_id"]').get_attribute('content').split(':')
    print(zen_object_id)
    documentId = zen_object_id[1]
    publicationPublisherId = zen_object_id[0]

    url_json = f'https://dzen.ru/api/comments/v2/root-comments?documentId=native%3A{documentId}&publicationPublisherId={publicationPublisherId}'
    r = requests.get(url_json).json()
    UsersByID = {v['uidSafe']: v['displayName'] for k, v in r['usersById'].items()}
    print(UsersByID)

    for block in r['items']:
        print(block)
        url_answer = block['entityData']['id']
        print(url_answer)

        if url_answer in links:
            print('Такой комментарий уже есть в списке')
            continue

        date = block['entityData']['createdTs']/1000

        if (time.time() - date) > 7 * 24 * 3600:
            print(f'--- Отзыв старше 30 дней = {date}.')
            continue

        date = datetime.fromtimestamp(timestamp_sec)
        # Форматирование даты
        formatted_date = date.strftime('%d.%m.%Y')
        print(formatted_date)

        #authorSafeUid = block['authorSafeUid']
        author = UsersByID[block['entityData']['authorSafeUid']]
        print(author)

        await generate_and_white(service=service,
                                 url_answer=url_answer,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)

async def check_ya(service, url, pattern, criteria, ss_id, project):
    print(f"New link = {url}")
    links = await pars_url(service, ss_id, project)
    ts = random.randint(5, max_sec)
    print(f'Wait {ts} sec...')
    await asyncio.sleep(ts)

    #playwright, browser, page = await get_playwright(url, headless=False)
    playwright, browser, page = await get_playwright(url)
    await page.evaluate("document.body.style.zoom=0.5")

    print('=> Rating By date')
    n = 0
    while n < 10:
        try:
            button_default = await page.query_selector('div[class="rating-ranking-view"]')
            await button_default.click()
            await asyncio.sleep(1)

            button_new = await page.query_selector('div[class="rating-ranking-view__popup-line"][aria-label="По новизне"]')
            await button_new.click()
            await asyncio.sleep(5)
            break

        except Exception as e:
            print('Error Click Review', e)
            await asyncio.sleep(5)
            n += 1

    print('=> Get blocks')

    break_on = False
    while break_on == False:
        blocks = await page.query_selector_all('div[class="business-reviews-card-view__review"]')
        print(len(blocks))

        for block in blocks:

            try:
                date_element = await block.query_selector(
                    'meta[itemprop="datePublished"]')  # Corrected selector (should be 'meta')
                date_content = await date_element.get_attribute('content')
                date = datetime.strptime(date_content, "%Y-%m-%dT%H:%M:%S.%fZ")

            except AttributeError as AE:
                date_element = await block.query_selector('span[class="business-review-view__date"]')
                date = await date_element.inner_text()

                month = await convert_date(date)
                if now_month != month:
                    continue

                else:
                    day = int(date.split(' ')[0])
                    year = current_date.year
                    date = datetime(year, month, day)

            if (current_date - date) > timedelta(days=days_ago):
                print(f'--- Отзыв старше {days_ago} дней. = {date}')
                break_on = True
                break

            org_answer = await block.query_selector('div[class="business-review-view__comment-expand"]')
            if org_answer:
                print('Есть ответ представителя компании')
                continue
            else:
                print('Ответа нет!')

            print('-> Click get link...')
            #button_share = await block.query_selector('span[class="inline-image _loaded icon"]')
            button_share = await block.query_selector('div[class="business-review-view__share-control"]')
            print('-> Click get link...')
            await button_share.click()
            print('-> Click get link...')
            await asyncio.sleep(3)

            button_open = await page.query_selector('input[class="input__control"]')
            url_answer = await button_open.get_attribute('value')
            print(url_answer)

            await page.keyboard.press('Escape')

            if url_answer in links:
                print('Такой комментарий уже есть в списке')
                continue

            author_text = await block.query_selector('span[itemprop="name"]')
            author = await author_text.inner_text()
            print(author)

            feedback_text =  await block.query_selector('span[class="business-review-view__body-text"]')
            feedback = await feedback_text.inner_text()
            print(feedback)

            formatted_date = date.strftime("%d.%m.%Y")
            print(formatted_date)

            await generate_and_white(service=service,
                                     url_answer=url_answer,
                                     author=author,
                                     formatted_date=formatted_date,
                                     ss_id=ss_id,
                                     project=project,
                                     feedback=feedback,
                                     pattern=pattern,
                                     criteria=criteria)


        print('Тут можно будет поставить скрол для загрузки доп отзывов')
        break

    await browser.close()
    await playwright.stop()









async def main():
    service = await get_service()

    url = 'https://yandex.ru/maps/org/sberbank_strakhovaniye/86304407603/reviews'
    url = 'https://yandex.ru/maps/org/ultra_city/204166540835/reviews/?ll=30.224730%2C60.035566&z=14'
    await check_ya(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", "Паритет")

if __name__ == '__main__':
    asyncio.run(main())


