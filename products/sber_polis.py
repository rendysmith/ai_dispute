import asyncio
import re
import traceback
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from typing import Optional

from utils.constants import empty_data
from utils.gs_editor import get_service, read_table_id, append_data_to_sheet_scopes, \
    append_data_to_sheet_cell, append_data_to_sheet_cells
from utils.user_agent import get_playwright, get_soup

from portals.portal_otzovik import check_captcha, get_feedback as get_feedback_otzovik
from portals.portal_banki import block_banki
from portals.portal_asn_news import get_feedback as get_feedback_asn

now = datetime.now()
current_date = now.strftime('%d.%m.%Y')

ss_id = '1lVTHhOPynrRk1JKYuBuIapeO7KCTs4Hc95EqGemjUDs'
project = 'SberInsurance'

max_days = 7


def today_midnight_utc() -> datetime:
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def review_is_too_old(date_obj: datetime, ref_midnight: datetime) -> bool:
    if date_obj.tzinfo is None:
        date_obj = date_obj.replace(tzinfo=timezone.utc)
    day = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
    return (ref_midnight - day) > timedelta(days=max_days)


async def otzovik_block_date(block) -> Optional[datetime]:
    date_content = await block.locator('div.review-postdate').get_attribute('content')
    if not date_content:
        return None
    return datetime.strptime(date_content[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)


async def parse_otzovik_page(page, page2, links, min_rating, max_rating, ref_midnight, project, source_link):
    blocks = await page.locator('div[class="item status4 mshow0"]').all()
    len_b = len(blocks)
    within_date_range = True
    datas_filter = await empty_data()

    for block in blocks:
        date_obj = await otzovik_block_date(block)
        if date_obj and review_is_too_old(date_obj, ref_midnight):
            within_date_range = False
            break

        rating = int(await block.locator('div[class="rating-score tooltip-right"]').inner_text())
        if not (min_rating <= rating <= max_rating):
            continue

        review_url_content = await block.locator('a.review-btn.review-read-link').get_attribute('href')
        review_url = f"https://otzovik.com{review_url_content}"
        if review_url in links:
            continue

        text = await get_feedback_otzovik(page2, review_url)
        if not await is_promotional_review(text):
            continue

        author = await block.locator('span[itemprop="name"]').inner_text()
        formatted_date = date_obj.strftime("%d.%m.%Y") if date_obj else ''
        datas_filter['Дата'].append(formatted_date)
        datas_filter['Текст'].append(text)
        datas_filter['Бренд'].append(project)
        datas_filter['Источник'].append('otzovik.com')
        datas_filter['Url'].append(review_url)
        datas_filter['Автор'].append(author)
        datas_filter['Оценка'].append(rating)
        datas_filter['Общий Url'].append(source_link)

    return len_b, datas_filter, within_date_range


async def parse_asn_news_page(page_url, links, min_rating, max_rating, ref_midnight, project, source_link):
    soup = await get_soup(page_url)
    blocks = soup.select('div.comments-bl_item')
    len_b = len(blocks)
    within_date_range = True
    datas_filter = await empty_data()
    datas_filter['Статус оценки'] = []

    for block in blocks:
        date_str = block.select_one('div.dashboard-post__date').text.strip()
        date_obj = datetime.strptime(date_str, '%d.%m.%Y').replace(tzinfo=timezone.utc)
        if review_is_too_old(date_obj, ref_midnight):
            within_date_range = False
            continue

        rating = int(block.select_one('div.comments-bl_item__head_mark').text)
        review_url = "https://www.asn-news.ru" + block.select_one('a.main_footer__comment-btn').get('href')
        if not (min_rating <= rating <= max_rating) or review_url in links:
            continue

        text = await get_feedback_asn(review_url)
        if not await is_promotional_review(text):
            continue

        author = block.select_one('div.main_head__user-name').text.strip()
        status = block.select_one('div.comments-bl_item__head_status').text.strip()
        datas_filter['Дата'].append(date_str)
        datas_filter['Текст'].append(text)
        datas_filter['Бренд'].append(project)
        datas_filter['Источник'].append('asn-news.ru')
        datas_filter['Url'].append(review_url)
        datas_filter['Автор'].append(author)
        datas_filter['Оценка'].append(rating)
        datas_filter['Общий Url'].append(source_link)
        datas_filter['Статус оценки'].append(status)

    return len_b, datas_filter, within_date_range

# Регулярное выражение вынесено из функции для производительности
PROMO_PATTERN = re.compile(
    r'('
    r'\d{3}[A-Za-zА-Яа-яЁё]{2,3}[\s№Nº_-]*[\d*]{8,}'  # Паттерн 1: Цифры+Буквы+Номер
    r'|'
    r'[A-Za-zА-Яа-яЁё*]{2,}[\s]*[\d*]{6,}'  # Паттерн 2: Маска/Буквы+Номер
    r'|'
    r'\b\d{10,}\b'  # Паттерн 3: Только длинные цифры
    r')',
    re.IGNORECASE | re.UNICODE
)

async def is_promotional_review(content):
    """
    Проверяет, содержится ли в заголовке или тексте отзыва номер полиса.
    """
    if not content:
        return False
    match = PROMO_PATTERN.search(content)
    return match is not None

async def pars_banki(service, project, link, links, min_rating, max_rating, last_page=1, idx=0):
    ref_midnight = today_midnight_utc()

    p, browser, context, page = await get_playwright()

    try:
        parsed_url = urlparse(link)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"

        within_date_range = True

        for current_page in range(last_page, 1000):
            page_url = f"{base_url}?page={current_page}"
            print("Page", page_url)
            await page.goto(page_url, wait_until="domcontentloaded")

            datas = await block_banki(page)

            if not datas.get("Дата"):
                continue

            len_d = len(datas["Дата"])
            print(f'Len D = {len_d}')

            first_date_obj = datetime.strptime(datas['Дата'][0], '%d.%m.%Y').replace(tzinfo=timezone.utc)
            if review_is_too_old(first_date_obj, ref_midnight):
                await append_data_to_sheet_cells(
                    service, ss_id, 'links', ['last_page', 'max_page'], idx + 2, [current_page, current_page]
                )
                return 'OK!'

            data_filter = await empty_data()
            if "Статус оценки" not in data_filter:
                data_filter["Статус оценки"] = []

            for i in range(len(datas["Текст"])):
                text = datas['Текст'][i]
                rating = int(datas['Оценка'][i])
                review_url = datas['Url'][i]
                date = datas['Дата'][i]
                date_obj = datetime.strptime(date, '%d.%m.%Y').replace(tzinfo=timezone.utc)

                if review_is_too_old(date_obj, ref_midnight):
                    within_date_range = False
                    continue

                if not (min_rating <= rating <= max_rating):
                    continue

                if review_url in links:
                    continue

                if await is_promotional_review(text):
                    data_filter['Дата'].append(date)
                    data_filter['Текст'].append(datas['Текст'][i])
                    data_filter['Бренд'].append(project)
                    data_filter['Источник'].append('banki.ru')
                    data_filter['Url'].append(review_url)
                    data_filter['Автор'].append(datas['Автор'][i])
                    data_filter['Оценка'].append(rating)
                    data_filter['Общий Url'].append(link)
                    data_filter['Статус оценки'].append(datas['Статус оценки'][i])

            await append_data_to_sheet_cells(
                service, ss_id, 'links', ['last_page', 'max_page'], idx + 2, [current_page, current_page]
            )

            if not within_date_range:
                if data_filter['Дата']:
                    await append_data_to_sheet_scopes(service, ss_id, project, data_filter)
                return 'OK!'

            if len_d < 25:
                if data_filter['Дата']:
                    await append_data_to_sheet_scopes(service, ss_id, project, data_filter)
                return 'OK!'

            if data_filter['Дата']:
                await append_data_to_sheet_scopes(service, ss_id, project, data_filter)

            await asyncio.sleep(5)

        return 'OK!'
    except Exception as e:
        print(f"Ошибка во время работы: {e}")

    finally:
        await page.close()
        await context.close()
        await browser.close()
        await p.stop()
    return 'OK!'

async def pars_otzovik(service, project, link, links, min_rating, max_rating, last_page=1, idx=0):
    p, browser, context, page = await get_playwright(blocked_resource=False, proxy_type='ru')
    p2, browser2, context2, page2 = await get_playwright(blocked_resource=False, proxy_type='ru')

    ref_midnight = today_midnight_utc()
    pages = 36

    try:
        parsed_url = urlparse(link)

        for current_page in range(last_page, 1000):
            page_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}{current_page}/?order=date_desc&ratio=Y"
            print("Page", page_url)
            await page.goto(page_url)
            await asyncio.sleep(5)

            await check_captcha(page)

            blocks = await page.locator('div[class="item status4 mshow0"]').all()
            if blocks:
                newest_date = await otzovik_block_date(blocks[0])
                if newest_date and review_is_too_old(newest_date, ref_midnight):
                    print(f'[{idx}] otzovik: самый новый отзыв на странице старше {max_days} дн., стоп')
                    await append_data_to_sheet_cells(
                        service, ss_id, 'links', ['last_page', 'max_page'], idx + 2, [current_page, current_page]
                    )
                    return 'OK!'

            len_b, datas_filter, within_date_range = await parse_otzovik_page(
                page, page2, links, min_rating, max_rating, ref_midnight, project, link
            )
            print(f'Len B: {len_b}')

            await append_data_to_sheet_cells(
                service, ss_id, 'links', ['last_page', 'max_page'], idx + 2, [current_page, current_page]
            )

            if not within_date_range:
                if datas_filter['Дата']:
                    await append_data_to_sheet_scopes(service, ss_id, project, datas_filter)
                return 'OK!'

            if datas_filter['Дата']:
                await append_data_to_sheet_scopes(service, ss_id, project, datas_filter)

            if len_b < pages:
                return 'OK!'

            await asyncio.sleep(5)

    except Exception as Ex:
        print(f'Error Ex1: {Ex}')
        traceback.print_exc()

    finally:
        await page.close()
        await context.close()
        await browser.close()
        await p.stop()

        await page2.close()
        await context2.close()
        await browser2.close()
        await p2.stop()

    return 'OK!'

async def pars_sravni(service, project, link, links, min_rating, max_rating, last_page=0, idx=0):
    ref_midnight = today_midnight_utc()
    ReviewObjectId = 147351
    PageSize = 10

    for PageIndex in range(last_page, 1000, 50):
        api_url = (
            f'https://www.sravni.ru/proxy-reviews/reviews/?'
            f'FilterBy=all&'
            f'NewIds=true&OrderBy=byDate&'
            f'PageIndex={PageIndex}&'
            f'PageSize={PageSize}&'
            f'Rated=4,5&'
            f'ReviewObjectId={ReviewObjectId}'
        )

        print(api_url)

        r_text = await get_soup(api_url, only_text=False)

        try:
            items = r_text['items']
            len_b = len(items)
        except Exception as Ex:
            return f'Error {Ex}'

        print(f'- Len = {len_b}')

        if items:
            first_date = datetime.fromisoformat(items[0]['date'].replace("Z", "+00:00"))
            if review_is_too_old(first_date, ref_midnight):
                await append_data_to_sheet_cells(
                    service, ss_id, 'links', ['last_page', 'max_page'], idx + 2, [PageIndex, PageIndex]
                )
                return 'OK!'

        datas = await empty_data()
        datas['Статус оценки'] = []
        within_date_range = True

        for item in items:
            date_obj = datetime.fromisoformat(item['date'].replace("Z", "+00:00"))
            if review_is_too_old(date_obj, ref_midnight):
                within_date_range = False
                break

            text = item['text']
            review_url = f"https://www.sravni.ru/strakhovaja-kompanija/sberbank-strah/otzyvy/{item['id']}/"

            if review_url in links:
                continue

            if not await is_promotional_review(text):
                continue

            formatted_date = date_obj.strftime("%d.%m.%Y")
            author = f"{item['authorName']} {item['authorLastName']}"
            rating = item['rating']

            rating_status = item['ratingStatus']
            status = 'Проверяем оценку' if rating_status == 'rateChecking' else 'Неизвестно'

            datas['Дата'].append(formatted_date)
            datas['Текст'].append(text)
            datas['Бренд'].append(project)
            datas['Источник'].append('sravni.ru')
            datas['Url'].append(review_url)
            datas['Автор'].append(author)
            datas['Оценка'].append(rating)
            datas['Общий Url'].append(link)
            datas['Статус оценки'].append(status)

        await append_data_to_sheet_cells(
            service, ss_id, 'links', ['last_page', 'max_page'], idx + 2, [PageIndex, PageIndex]
        )

        if not within_date_range:
            if datas['Дата']:
                await append_data_to_sheet_scopes(service, ss_id, project, datas)
            return 'OK!'

        if datas['Дата']:
            await append_data_to_sheet_scopes(service, ss_id, project, datas)

        if len_b < PageSize:
            return 'OK!'

    return 'OK!'

async def pars_asn_news(service, project, link, links, min_rating, max_rating, last_page=1, idx=0):
    pages = 10
    ref_midnight = today_midnight_utc()

    try:
        parsed_url = urlparse(link)

        for current_page in range(last_page, 1000):
            page_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}?page={current_page}&type=company&filter=positive"
            print("Page:", page_url)

            len_b, datas_filter, within_date_range = await parse_asn_news_page(
                page_url, links, min_rating, max_rating, ref_midnight, project, link
            )

            await append_data_to_sheet_cells(
                service, ss_id, 'links', ['last_page', 'max_page'], idx + 2, [current_page, current_page]
            )

            if not within_date_range:
                if datas_filter['Дата']:
                    await append_data_to_sheet_scopes(service, ss_id, project, datas_filter)
                return 'OK!'

            if datas_filter['Дата']:
                await append_data_to_sheet_scopes(service, ss_id, project, datas_filter)

            if len_b < pages:
                return 'OK!'

            await asyncio.sleep(5)

    except Exception as Ex:
        print(f'--- Error Ex = {Ex}')
        traceback.print_exc()

    return 'OK!'

async def main_sber_polis():
    service = await get_service()
    df = await read_table_id(service, ss_id, 'links')
    print(df)

    try:
        df_links = await read_table_id(service, ss_id, project)
        links = df_links['Url'].tolist()
    except Exception as Ex:
        print(f'Error Ex: {Ex}')
        links = []

    print(f'Len Links = {len(links)}')

    for idx, row in df.iterrows():
        status =row['status']
        last_day = row['last_day']

        if status == 'OK!' and current_date == last_day:
            continue

        try:
            last_page = int(row['last_page'])
        except:
            last_page = 0

        min_rating = int(row['min_rating'])
        max_rating = int(row['max_rating'])
        link = row['link']

        if 'otzovik' in link:
            status = await pars_otzovik(service, project, link, links, min_rating, max_rating, last_page, idx)

        elif 'asn-news' in link:
            status = await pars_asn_news(service, project, link, links, min_rating, max_rating, last_page, idx)

        elif 'banki' in link:
            status = await pars_banki(service, project, link, links, min_rating, max_rating, last_page, idx)

        elif 'sravni' in link:
            status = await pars_sravni(service, project, link, links, min_rating, max_rating, last_page, idx)

        await append_data_to_sheet_cell(service, ss_id, 'links', "last_page", idx + 2, 0)

        columns = ['status', 'last_day']
        datas = [status, current_date]
        await append_data_to_sheet_cells(service, ss_id, 'links', columns, idx+2, datas)

if "__main__" == __name__:
    asyncio.run(main_sber_polis())