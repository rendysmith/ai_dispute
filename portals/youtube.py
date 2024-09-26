import asyncio
import os
import random
import time
from datetime import datetime

from dotenv import load_dotenv

from utils.ai_module import generate_and_white
from utils.compressor import compress_string
from utils.gs_editor import get_service, pars_url

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

current_date = datetime.now()
now_month = current_date.month
now_year = current_date.year

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

async def check_youtube(service, url, pattern, criteria, ss_id, project, playwright, browser, page):
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
    await page.wait_for_timeout(5000)

    for _ in range(3):  # Прокрутка 10 раз
        await page.evaluate("window.scrollBy(0, window.innerHeight)")
        await page.wait_for_timeout(1000)  # Ожидание 1 секунды между скроллами

    blocks = await page.query_selector_all('ytd-comment-view-model[id="comment"]')
    print(len(blocks))

    if len(blocks) == 0:
        blocks = await page.query_selector_all('ytd-comment-thread-renderer[class="style-scope ytd-item-section-renderer"]')
        print(len(blocks))

    if len(blocks) == 0:
        await browser.close()
        await playwright.stop()
        return

    for block in blocks:
        try:
            date_element = await block.query_selector_all('a[class="yt-simple-endpoint style-scope ytd-comment-view-model"][href]')  # Corrected selector (should be 'meta')
            date = await date_element[-1].inner_text()
            print('date -', date)
            if any(dt in date for dt in ['год', 'year']):
                print(f'Next...({date})')
                continue

            elif any(dt in date for dt in ['дн', 'day', 'недел', 'week']):
                print(f'Next...({date})')

            else:
                continue

            date_split = date.split(' ')
            print(date_split)

            if len(date_split) == 3:
                day_int = int(date_split[0])

                if any(dt in date for dt in ['дн', 'day']):
                    sec = day_int * 24 * 3600

                elif any(dt in date for dt in ['недел', 'week']):
                    sec = day_int * 7 * 24 * 3600

            else:
                continue

        except AttributeError as AE:
            print('Error AE', AE)
            continue

        except Exception as Ex:
            print('Error Ex', Ex)
            continue

        feedback_text =  await block.query_selector('span[class="yt-core-attributed-string yt-core-attributed-string--white-space-pre-wrap"]')
        feedback = await feedback_text.inner_text()
        print(feedback)

        url_answer = await compress_string(feedback)

        if url_answer in links:
            print('Такой комментарий уже есть в списке')
            continue

        try:
            author_text = await block.query_selector('span[class=" style-scope ytd-comment-view-model style-scope ytd-comment-view-model"]')
            author = await author_text.inner_text()

        except AttributeError as AE:
            print(f'Error AE: {AE}, Next...')
            author_text = await block.query_selector('div[id="text-container"]')
            author = await author_text.inner_text()

        print(author)

        date = datetime.fromtimestamp(time.time() - sec)
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


    await browser.close()
    await playwright.stop()









async def main():
    service = await get_service()
    url = 'https://www.youtube.com/watch?v=ExrG6AhR-wI'
    await check_youtube(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", 1)

if __name__ == '__main__':
    asyncio.run(main())


