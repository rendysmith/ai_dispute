import asyncio
import random
import os

from datetime import datetime, timedelta

from utils.gs_editor import get_service, pars_url, append_data_to_sheet_scope
from utils.ai_module import generate_and_white
from utils.user_agent import get_playwright

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

async def check_ya(service, url, pattern, criteria, ss_id, project, playwright, browser, page):
    url_split = url.split('/')
    id_org = url_split[5]
    top_url = f'https://yandex.ru/maps/org/{id_org}'

    datas = {'project': project,
             'url': url,
             'top_url': top_url}

    await append_data_to_sheet_scope(service, ss_id, 'unique_url', datas)

    print(f"New link = {url}")

    #playwright, browser, page = await get_playwright(url, headless=False)
    #playwright, browser, page = await get_playwright(url)

    links = await pars_url(service, ss_id, project)
    ts = random.randint(5, max_sec)
    print(f'Wait {ts} sec...')
    await asyncio.sleep(ts)

    if not page:
        await browser.close()
        await playwright.stop()
        return 'Сайт не отдал данные.'

    await page.evaluate("document.body.style.zoom=0.5")

    print('=> Rating By date')
    n = 0
    while True:
        if n == 10:
            await browser.close()
            await playwright.stop()
            return 'Сайт не отдал данные'

        try:
            button_default = await page.query_selector('div[class="rating-ranking-view"]')
            await button_default.click()
            await asyncio.sleep(1)

            button_new = await page.query_selector('div[class="rating-ranking-view__popup-line"][aria-label="По новизне"]')
            await button_new.click()
            await asyncio.sleep(5)
            break

        except Exception as e:
            print('Error Click Review:', e)
            await asyncio.sleep(5)
            n += 1

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

            month = await convert_date(month_str)

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
            break_on = True
            break

        org_answer = await block.query_selector('div[class="business-review-view__comment-expand"]')
        if org_answer:
            print('Есть ответ представителя компании')
            continue
        else:
            print('Ответа нет!')

        n = 0
        while True:
            if n == 10:
                await browser.close()
                await playwright.stop()
                return 'Сайт не предоставил данные'

            try:
                #button_share = await block.query_selector('span[class="inline-image _loaded icon"]')
                button_share = await block.query_selector('div[class="business-review-view__share-control"]')
                print('-> Click share')
                await button_share.click()
                print('-> Click share - OK!')
                await asyncio.sleep(3)
                break

            except:
                n += 1
                await asyncio.sleep(3)

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
    url = 'https://yandex.ru/maps/org/165131132044/reviews'
    url = 'https://yandex.kz/maps/org/schastye/187776871438/reviews/?ll=66.272509%2C56.632288&utm_source=review&z=16'

    playwright, browser, page = await get_playwright(url)
    await check_ya(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", 1, playwright, browser, page)

if __name__ == '__main__':
    asyncio.run(main())


