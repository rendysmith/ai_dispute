import asyncio
import json
import os

from datetime import datetime, timedelta

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchWindowException

from dotenv import load_dotenv

from utils.central_module import wait_for_portal
from utils.constants import months
from utils.ai_module import generate_and_white
from utils.gs_editor import get_service, pars_url, append_data_to_sheet_scope
from utils.user_agent import get_selenium_proxy

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

current_date = datetime.now()
now_month = current_date.month

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))
timeout = 10000


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


async def check_ya(service, link, pattern, criteria, ss_id, project, driver):
    print(f'\nLink: {link}')
    driver.get(link)
    await wait_for_portal() #Время ожидания

    url = driver.current_url
    print("current url", url)

    id_org = await get_id_org(url)
    top_url = f'https://yandex.ru/maps/org/{id_org}'
    print('top_url', top_url)

    datas = {'project': project,
             'url': url,
             'top_url': top_url}

    await append_data_to_sheet_scope(service, ss_id, 'unique_url', datas)

    print(f"New link = {url}")
    driver.get(top_url + '/reviews')
    driver.execute_script("document.body.style.zoom='0.5'")
    await asyncio.sleep(3)

    #await page.wait_for_selector('script[class="state-view"]', timeout=timeout)
    #data_site_content = await page.query_selector('script[class="state-view"]')
    #data_site = await data_site_content.inner_text()

    data_site = driver.find_element(By.CSS_SELECTOR, 'script.state-view').text
    dictionary = json.loads(data_site)
    #pprint(dictionary)

    if dictionary['stack'][0].get("results"):
        reviews = dictionary['stack'][0]['results']['items'][0]['reviewResults']['reviews']

    elif dictionary['stack'][0].get("response"):
        reviews = dictionary['stack'][0]['response']['items'][0]['reviewResults']['reviews']

    else:
        reviews = []

    len_r = len(reviews)

    if len_r == 0:
        return

    links = await pars_url(service, ss_id, project)

    for rew in reviews:
        #pprint(rew)
        if rew.get('text'):
            date_content = rew['updatedTime']
            date = datetime.strptime(date_content, "%Y-%m-%dT%H:%M:%S.%fZ")
            if (current_date - date) > timedelta(days=days_ago):
                print(f'--- Отзыв старше {days_ago} дней. = {date}')
                continue

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


async def check_ya_old2(service, url, pattern, criteria, ss_id, project, playwright, browser, page):
    links = await pars_url(service, ss_id, project)

    if not page:
        return 'Сайт не отдал данные.'

    url = page.url

    id_org = await get_id_org(url)

    top_url = f'https://yandex.ru/maps/org/{id_org}'

    datas = {'project': project,
             'url': url,
             'top_url': top_url}

    await append_data_to_sheet_scope(service, ss_id, 'unique_url', datas)

    print(f"New link = {url}")
    await page.goto(top_url + '/reviews')
    await page.evaluate("document.body.style.zoom=0.5")

    #await page.wait_for_selector('script[class="state-view"]', timeout=timeout)
    data_site_content = await page.query_selector('script[class="state-view"]')
    data_site = await data_site_content.inner_text()

    dictionary = json.loads(data_site)
    #pprint(dictionary)

    if dictionary['stack'][0].get("results"):
        reviews = dictionary['stack'][0]['results']['items'][0]['reviewResults']['reviews']

    elif dictionary['stack'][0].get("response"):
        reviews = dictionary['stack'][0]['response']['items'][0]['reviewResults']['reviews']

    else:
        reviews = []

    len_r = len(reviews)

    if len_r == 0:
        await browser.close()
        await playwright.stop()
        return

    for rew in reviews:
        #pprint(rew)
        if rew.get('text'):
            date_content = rew['updatedTime']
            date = datetime.strptime(date_content, "%Y-%m-%dT%H:%M:%S.%fZ")
            if (current_date - date) > timedelta(days=days_ago):
                print(f'--- Отзыв старше {days_ago} дней. = {date}')
                continue

            author = rew['author']['name']
            #print(author)

            url_answer = rew['reviewId']
            #print(url_answer)
            if url_answer in links:
                print('Такой комментарий уже есть в списке')
                continue

            feedback = rew['text']
            print(feedback)

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
    #
    await browser.close()
    await playwright.stop()
    #
    #
    #
    #
    #
    # print('**************************************************')
    # businessId = id_org
    # csrfToken = dictionary['config']['csrfToken']
    # print(csrfToken)
    #
    # print('----------------------------------')
    #
    # reqId = await get_requestId(dictionary)
    # print(reqId)
    #
    # sessionId = dictionary['config']['counters']['analytics']['sessionId']
    # print(sessionId)
    #
    # url = (f'https://yandex.kz/maps/api/business/fetchReviews?ajax=1'
    #        f'&businessId={businessId}'
    #        f'&csrfToken={csrfToken}'
    #        f'&locale=ru_KZ'
    #        f'&page=1'
    #        f'&pageSize=50'
    #        f'&ranking=by_time'
    #        f'&reqId={reqId}'
    #        f'&s=2862124894'
    #        f'&sessionId={sessionId}')
    #
    # print(url)
    # r = requests.get(url)
    # print(r)
    #
    # print(r.json())
    #

async def get_id_org(url):
    url_split = url.split('/')
    for k, v in enumerate(url_split):
        if v.isdigit():
            return v

async def check_ya_old(service, url, pattern, criteria, ss_id, project, playwright, browser, page):
    links = await pars_url(service, ss_id, project)

    if not page:
        # await browser.close()
        # await playwright.stop()
        return 'Сайт не отдал данные.'

    url = page.url

    id_org = await get_id_org(url)

    top_url = f'https://yandex.ru/maps/org/{id_org}'

    datas = {'project': project,
             'url': url,
             'top_url': top_url}

    await append_data_to_sheet_scope(service, ss_id, 'unique_url', datas)

    print(f"New link = {url}")

    await page.goto(top_url + '/reviews')
    await page.evaluate("document.body.style.zoom=0.5")

    print('=> Rating By date')

    for n in range(12):
        if n == 10:
            await browser.close()
            await playwright.stop()
            return 'Сайт не отдал данные'

        try:
            #button_default = await page.query_selector('div[class="rating-ranking-view"]')
            button_default = await page.wait_for_selector('div[class="rating-ranking-view"]', timeout=timeout)
            await button_default.click()
            #await asyncio.sleep(1)
            print('Click role...')

            #button_new = await page.query_selector('div[class="rating-ranking-view__popup-line"][aria-label="По новизне"]')
            button_new = await page.wait_for_selector('div[class="rating-ranking-view__popup-line"][role="button"]', timeout=timeout)
            print(1)
            button_new = await page.query_selector_all('div[class="rating-ranking-view__popup-line"][role="button"]')
            print(len(button_new))
            print(2)
            await button_new[1].click()
            print(3)
            #await asyncio.sleep(3)
            break

        except Exception as Ex:
            print(f"Попытка не удалась: {Ex}")
            if n == 5:  # Если не последняя попытка
                await page.reload()  # Перезагрузить страницу

            elif n == 10:
                await browser.close()
                await playwright.stop()
                return 'Не удалось нажать на кнопку.'  # Вернуть ошибку

    print('=> Get blocks')

    blocks = await page.query_selector_all('div[class="business-reviews-card-view__review"]')
    print('Len ', len(blocks))

    if len(blocks) == 0:
        await browser.close()
        await playwright.stop()
        return

    for block in blocks:
        try:
            date_element = await block.query_selector('meta[itemprop="datePublished"]')  # Corrected selector (should be 'meta')
            date_content = await date_element.get_attribute('content')
            date = datetime.strptime(date_content, "%Y-%m-%dT%H:%M:%S.%fZ")

        except AttributeError as AE:
            print(f'AE: {AE}')
            date_element = await block.query_selector('span[class="business-review-view__date"]')
            date = await date_element.inner_text()
            print('Date =', date)

            date_split = date.split(' ')
            print("date_split", date_split)

            if len(date_split) == 2:
                month_str = date_split[1]

            elif len(date_split) == 3:
                month_str = date_split[1]
                year_str = date_split[2]

                if int(year_str) != current_date.year:
                    print('Next year >>>')
                    continue

            month = await months(month_str)

            if now_month != month:
                print('Next month >>>')
                continue

            else:
                day = int(date_split[0])
                year = current_date.year
                date = datetime(year, month, day)

            print("date =", date)

        if (current_date - date) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней. = {date}')
            break

        org_answer = await block.query_selector('div[class="business-review-view__comment-expand"]')
        if org_answer:
            print('Есть ответ представителя компании')
            continue
        else:
            print('Ответа нет!')

        for n in range(12):
            if n == 10:
                await browser.close()
                await playwright.stop()
                return 'Сайт не предоставил данные'

            try:
                #button_share = await block.query_selector('span[class="inline-image _loaded icon"]')
                #button_share = await block.query_selector('div[class="business-review-view__share-control"]')
                button_share = await page.wait_for_selector('div[class="business-review-view__share-control"]', timeout=5000)
                print('-> Click share')
                await button_share.click()
                print('-> Click share - OK!')
                await asyncio.sleep(3)
                break

            except:
                await asyncio.sleep(2)

        button_open = await page.query_selector('input[class="input__control"]')
        url_answer = await button_open.get_attribute('value')
        #print(url_answer)

        await page.keyboard.press('Escape')

        if url_answer in links:
            print('Такой комментарий уже есть в списке')
            continue

        author_text = await block.query_selector('span[itemprop="name"]')
        author = await author_text.inner_text()
        #print(author)

        feedback_text =  await block.query_selector('span[class="business-review-view__body-text"]')
        feedback = await feedback_text.inner_text()
        #print(feedback)

        formatted_date = date.strftime("%d.%m.%Y")
        #print(formatted_date)

        await generate_and_white(service=service,
                                 url_answer=url_answer,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)

    await browser.close()
    await playwright.stop()









async def main():
    service = await get_service()

    url = 'https://yandex.ru/maps/org/artstudio_moskovsky/125846534919/?ll=30.329628%2C59.907103&mode=search&sll=30.301828%2C59.912472&sspn=0.022573%2C0.006756&text=Artstudio%20Moskovsky&z=14.86'
    #url = 'https://yandex.ru/maps/org/124956693444/reviews'
    #url = 'https://yandex.kz/maps/org/schastye/187776871438/reviews/?ll=66.272509%2C56.632288&utm_source=review&z=16'
    #url = 'https://yandex.kz/maps/org/krylya/115857625887/reviews/?ll=65.263154%2C57.147658&utm_source=review&z=16'

    driver = await get_selenium_proxy()
    await check_ya(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", 1, driver)

if __name__ == '__main__':
    asyncio.run(main())


