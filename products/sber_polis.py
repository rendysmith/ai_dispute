import asyncio
import os.path
import traceback
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
import re

from utils.constants import empty_blocks, empty_data
from utils.gs_editor import get_service, read_table_id, append_data_to_sheet_scope, append_data_to_sheet_scopes, \
    append_data_to_sheet_cell, append_data_to_sheet_cells
from utils.user_agent import get_playwright, get_soup, get_data_with_proxy, get_data_without_proxy

from portals.portal_otzovik import blocks_otzovik, check_captcha
from portals.portal_banki import block_banki
from portals.portal_sravni import block_sravni, get_ReviewObjectId
from portals.portal_asn_news import block_asn_news

core_path = os.path.dirname(os.path.dirname(__file__))

now = datetime.now()
current_date = now.strftime('%d.%m.%Y')

ss_id = '1lVTHhOPynrRk1JKYuBuIapeO7KCTs4Hc95EqGemjUDs'
project = 'SberInsurance'

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
    # Используем фиксированную точку отсчета времени
    today_midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    p, browser, context, page = await get_playwright()

    try:
        # Очищаем URL от рекламных хвостов (типа ?ysclid=...) для корректной пагинации
        parsed_url = urlparse(link)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"

        within_date_range = True

        for current_page in range(last_page, 1000):
            # Формируем ссылку на конкретную страницу (решает проблему необновляемого JSON)
            page_url = f"{base_url}?page={current_page}"
            print("Page", page_url)
            await page.goto(page_url, wait_until="domcontentloaded")

            datas = await block_banki(page) #Получение блоков от сайта

            if not datas.get("Дата"):
                continue

            len_d = len(datas["Дата"])
            print(f'Len D = {len_d}')

            data_filter = await empty_data()
            if "Статус оценки" not in data_filter:
                data_filter["Статус оценки"] = []

            for i in range(len(datas["Текст"])):
                text = datas['Текст'][i]
                rating = int(datas['Оценка'][i])
                review_url = datas['Url'][i]
                date = datas['Дата'][i]
                date_obj = datetime.strptime(date, '%d.%m.%Y').replace(tzinfo=timezone.utc)
                
                if (today_midnight - date_obj) > timedelta(days=30):
                    within_date_range = False
                    continue

                if min_rating <= rating <= max_rating:
                    pass
                else:
                    continue

                # Пропуск, если дубликат
                if review_url in links:
                    continue

                if is_promotional_review(text):
                    data_filter['Дата'].append(date)
                    data_filter['Текст'].append(datas['Текст'][i])
                    data_filter['Бренд'].append(project)
                    data_filter['Источник'].append('banki.ru')
                    data_filter['Url'].append(review_url)
                    data_filter['Автор'].append(datas['Автор'][i])
                    data_filter['Оценка'].append(rating)
                    data_filter['Общий Url'].append(link)
                    data_filter['Статус оценки'].append(datas['Статус оценки'][i])

            columns = ['last_page', 'max_page']
            fixdatas = [current_page, current_page]
            await append_data_to_sheet_cells(service,
                                            ss_id,
                                            'links',
                                             columns,
                                             idx + 2,
                                             fixdatas)

            if not within_date_range:
                return 'OK!'

            if len_d < 25:
                return 'OK!'

            await asyncio.sleep(5)

            if not data_filter["Дата"] and len_d == 25:
                continue

            await append_data_to_sheet_scopes(service, ss_id, project, data_filter)
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

    today_midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    pages = 36
    current_date = True

    try:
        # Очищаем URL от рекламных хвостов (типа ?ysclid=...) для корректной пагинации
        parsed_url = urlparse(link)

        for current_page in range(last_page, 1000):
            # Формируем ссылку на конкретную страницу (решает проблему необновляемого JSON)
            page_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}{current_page}/?order=date_desc&ratio=Y"
            print("Page", page_url)
            await page.goto(page_url)
            await asyncio.sleep(5)

            await check_captcha(page)

            blocks = await page.locator('div[class="item status4 mshow0"]').all()
            len_b = (len(blocks))
            print(f'Len B: {len_b}')

            datas = await blocks_otzovik(page, page2, links, min_rating, max_rating)  # Получение блоков от сайта

            if datas == [] and len_b == pages:
                continue

            datas_filter = await empty_data()

            for i in range(len(datas['Дата'])):
                text = datas['Текст'][i]
                date = datas['Дата'][i]

                date_obj = datetime.strptime(date, '%d.%m.%Y').replace(tzinfo=timezone.utc)

                if (today_midnight - date_obj) > timedelta(days=30):
                    current_date = False
                    continue

                if await is_promotional_review(text):
                    datas_filter['Дата'].append(date)
                    datas_filter['Текст'].append(text)
                    datas_filter['Бренд'].append(project)
                    datas_filter['Источник'].append('otzovik.com')
                    datas_filter['Url'].append(datas['Url'][i])
                    datas_filter['Автор'].append(datas['Автор'][i])
                    datas_filter['Оценка'].append(datas['Оценка'][i])
                    datas_filter['Общий Url'].append(link)

            columns = ['last_page', 'max_page']
            fixdatas = [current_page, current_page]
            await append_data_to_sheet_cells(service,
                                             ss_id,
                                             'links',
                                             columns,
                                             idx + 2,
                                             fixdatas)

            if not datas_filter["Дата"] and len_b == pages:
                continue

            await append_data_to_sheet_scopes(service, ss_id, project, datas_filter)

            if not current_date:
                return 'OK!'

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
    now = datetime.now(timezone.utc)
    ReviewObjectId = 147351
    PageSize = 10
    current_date = True

    for PageIndex in range(last_page, 1000, 50):
        link = (f'https://www.sravni.ru/proxy-reviews/reviews/?'
                f'FilterBy=all&'
                f'NewIds=true&OrderBy='
                f'highRateFirst&'
                f'PageIndex={PageIndex}&'
                f'PageSize={PageSize}&'
                f'Rated=4,5&'
                f'ReviewObjectId={ReviewObjectId}')

        print(link)

        r_text = await get_soup(link, only_text=False)

        try:
            len_b = len(r_text['items'])

        except Exception as Ex:
            return f'Error {Ex}'

        print(f'- Len = {len_b}')

        datas = await empty_data()
        datas['Статус оценки'] = []

        for i in r_text['items']:
            text = i['text']
            review_url = f"https://www.sravni.ru/strakhovaja-kompanija/sberbank-strah/otzyvy/{i['id']}/"

            if review_url in links:
                continue

            if await is_promotional_review(text):
                date_obj = datetime.fromisoformat(i['date'].replace("Z", "+00:00"))

                # 3. Проверяем, старше ли дата, чем 30 дней
                if (now - date_obj) > timedelta(days=30):
                    current_date = False
                    break

                formatted_date = date_obj.strftime("%d.%m.%Y")
                author = f"{i['authorName']} {i['authorLastName']}"
                rating = i['rating']

                ratingStatus = i['ratingStatus']
                if ratingStatus == 'rateChecking':
                    status = 'Проверяем оценку'
                else:
                    status = 'Неизвестно'

                datas['Дата'].append(formatted_date)
                datas['Текст'].append(text)
                datas['Бренд'].append(project)
                datas['Источник'].append('sravni.ru')
                datas['Url'].append(review_url)
                datas['Автор'].append(author)
                datas['Оценка'].append(rating)
                datas['Общий Url'].append(link)
                datas['Статус оценки'].append(status)

        columns = ['last_page', 'max_page']
        fixdatas = [PageIndex, PageIndex]
        await append_data_to_sheet_cells(service, ss_id,
                                         'links',
                                         columns,
                                         idx + 2,
                                         fixdatas)

        if not datas['Дата'] and len_b == PageSize:
            continue

        await append_data_to_sheet_scopes(service, ss_id, project, datas)

        if len_b < PageSize:
            return 'OK!'

        if not current_date:
            return 'OK!'

async def pars_asn_news(service, project, link, links, min_rating, max_rating, last_page=1, idx=0):
    pages = 10
    current_date = True
    today_midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        # Очищаем URL от рекламных хвостов (типа ?ysclid=...) для корректной пагинации
        parsed_url = urlparse(link)

        for current_page in range(last_page, 1000):
            # Формируем ссылку на конкретную страницу (решает проблему необновляемого JSON)
            page_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}?page={current_page}&type=company&filter=positive"
            print("Page:", page_url)

            len_b, datas = await block_asn_news(page_url, links, min_rating, max_rating)  # Получение блоков от сайта

            if datas == [] and len_b == pages:
                continue

            datas_filter = await empty_data()
            datas_filter['Статус оценки'] = []

            for i in range(len(datas['Дата'])):
                text = datas['Текст'][i]
                date = datas['Дата'][i]
                date_obj = datetime.strptime(date, '%d.%m.%Y').replace(tzinfo=timezone.utc)

                if (today_midnight - date_obj) > timedelta(days=30):
                    current_date = False
                    continue

                if await is_promotional_review(text):
                    datas_filter['Дата'].append(date)
                    datas_filter['Текст'].append(datas['Текст'][i])
                    datas_filter['Бренд'].append(project)
                    datas_filter['Источник'].append('asn-news.ru')
                    datas_filter['Url'].append(datas['Url'][i])
                    datas_filter['Автор'].append(datas['Автор'][i])
                    datas_filter['Оценка'].append(datas['Оценка'][i])
                    datas_filter['Общий Url'].append(link)
                    datas_filter['Статус оценки'].append(datas['Статус оценки'][i])

            columns = ['last_page', 'max_page']
            fixdatas = [current_page, current_page]
            await append_data_to_sheet_cells(service,
                                             ss_id,
                                             'links',
                                             columns,
                                             idx + 2,
                                             fixdatas)

            if not datas_filter["Дата"] and len_b == pages:
                continue

            await append_data_to_sheet_scopes(service, ss_id, project, datas_filter)

            if not current_date:
                return 'OK!'

            if len_b < pages:
                return 'OK!'

            await asyncio.sleep(5)

    except Exception as Ex:
        print(f'--- Error Ex = {Ex}')
        traceback.print_exc()

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
    asyncio.run(main())