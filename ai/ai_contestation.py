import asyncio
import json
import os
import re
from datetime import datetime

from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

import pandas as pd

from models.mdl_tables import ForumRules
from portals.dreamjob import extract_review_text
from portals.otzovru import blocks_otzovru, get_feedback_otzovru
from portals.portal_2gis import get_id_obj
from portals.portal_otzovik import check_captcha, date_convert, get_feedback
from portals.portal_tripadvisor import blocks_tripadvisor
from portals.portal_ya import get_base_url, get_rrr
from portals.portal_zoon import zoon_blocks
from portals.pravda_sotrudnikov import blocks_pravda

from utils.ai_module import get_answer_ai
from utils.central_module import get_hpo
from utils.constants import empty_data, months
from utils.db_loader import read_data_from_db_filter
from utils.gs_editor import get_service, get_table_scope, read_table_id, append_data_to_sheet_cell, \
    append_data_to_sheet_cells, append_data_to_sheet_scopes
from utils.user_agent import get_soup, get_soup_bs4, get_soup_curl_cffi, get_playwright, get_playwright_irec

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

max_sec = int(os.environ.get("MAX_SEC"))

username = os.environ.get("HOST_USERNAME")
password = os.environ.get("HOST_PASSWORD")
auth = HTTPBasicAuth(username, password)

# headless/proxy: env-переопределение для контейнера (k8s), иначе автоопределение по IP.
# Инициализация ленивая: под uvicorn модуль импортируется внутри запущенного event loop,
# поэтому asyncio.run на уровне модуля недопустим.
_headless_env = os.environ.get("HEADLESS")
_proxy_env = os.environ.get("PROXY_ON")
if _headless_env is not None or _proxy_env is not None:
    headless = _headless_env.lower() in ("1", "true", "yes") if _headless_env is not None else True
    proxy_on = _proxy_env.lower() in ("1", "true", "yes") if _proxy_env is not None else False
    only_text = False
    _hpo_loaded = True
else:
    headless = proxy_on = only_text = None
    _hpo_loaded = False


async def _ensure_hpo():
    """Определяет headless/proxy один раз за процесс (по IP текущего сервера)."""
    global headless, proxy_on, only_text, _hpo_loaded
    if _hpo_loaded:
        return
    headless, proxy_on, only_text = await get_hpo()
    _hpo_loaded = True

text = """
Ты модератор сайта {source},
Посмотри следующий комментарий: 
------------НАЧАЛО КОММЕНТАРИЯ--------------
{comment} 
------------КОНЕЦ КОММЕНТАРИЯ---------------
Определите, нарушает ли данный комментарий какое-либо из следующих правил площадки: 
------------НАЧАЛО ПРАВИЛ ПРОЩАДКИ-------------
{rule} 
------------КОНЕЦ ПРАВИЛ ПРОЩАДКИ--------------
Если комментарий нарушает какое-либо правило, ОБЯЗАТЕЛЬНО, укажи какое именно правило он нарушает, процитируй его и укажи номер, например: 
'*новая строка* *Порядковый номер строки, например*: Пункт правила и его текст и обязательно текст отзыва или его часть которое нарушает правило'.  
В противном случае укажите, что он не нарушает никаких правил.
Так же тебе нужно оценить вероятность удаление отзыва в процентном соотношении основываясь на указанных правилах выше, 
где 
80-100% - можно удалить комментарий
50-79% - вероятность удаления сомнительна
<49% - нарушений нет либо они не значительные, нельзя удалить комментарий

Ты должен выдать результат в формате списка [], 
где 
первый - элемент будет процент удаления, 
второй - резюме о нарушениях правил площадки если таковы будут
Оба элемента должны быть в формате string, т.е. в кавычках. 
Перед выполнением прочитай задание еще раз.
"""


async def get_links(service, ss_id, project):
    try:
        df_links = await read_table_id(service, ss_id, project)
        links = df_links['Url'].tolist()
    except:
        links = []

    return links


async def review_analysis(worktable_id, tab_name):
    '''Функция для анализа отзыва'''

    service = await get_service()
    sem = asyncio.Semaphore(3)  # максимум 3 одновременных задач

    status, rules_db = await read_data_from_db_filter(ForumRules)

    if status:
        if len(rules_db) > 0:
            rules_map = {r.forum_name: r.forum_rule for r in rules_db}

        else:
            print(f'Return: Len {len(rules_db)}')
            return
    else:
        print(f'Return: Status {status}: {rules_db}')
        return

    try:
        df = await get_table_scope(service, worktable_id, tab_name)
        print(df)

    except Exception as Ex:
        print(f"Error: {Ex}")
        return

    columns = ['Вероятность удаления', 'Текст для поддержки']

    async def rec_datas(idx, row):
        print(f'\nIDX = {idx}')
        probably_delete = row[columns[0]]
        text_support = row[columns[1]]

        if pd.notnull(probably_delete) and pd.notnull(text_support):
            print(f'IDX {idx} NOT Full 2')
            return

        brand = row['Бренд']
        link = row['Url']
        comment = row['Текст']
        source = row['Источник']

        if 'yandex.ru/maps' in source:
            project = 'yandex_maps'

        else:
            project = source.split('.')[0]

        print("Project: ", project)

        rule = rules_map.get(project)
        prompt = text.format(source=source, comment=comment, rule=rule)
        result = await get_answer_ai(auth, prompt)
        print(result)

        if not result or not isinstance(result, str):
            print(f'ERROR AI: invalid result: {result}')
            return

        try:
            result = eval(result)
            if '49' in result[0]:
                pass
            else:
                result[1] = (f"Здравствуйте, "
                             f"Я представляю интересы компании '{brand}' и хочу обратиться с просьбой удалить отзыв по ссылке {link}. "
                             f"Отзыв содержит нарушение:\n") + result[1]

            await append_data_to_sheet_cells(service, worktable_id, brand, columns, idx + 2, result)

        except (SyntaxError, TypeError) as SE:
            print(f'ERROR: {SE}')

        finally:
            await asyncio.sleep(5)

    async def rec_datas_limited(idx, row):
        async with sem:
            return await rec_datas(idx, row)

    tasks = [
        asyncio.create_task(rec_datas_limited(idx, row))
        for idx, row in df.iterrows()
    ]
    await asyncio.gather(*tasks)


async def pars_dreamjob(service, url_top, ss_id, project, links, rating_max, idx_last_page, last_page=1):
    """Функция для получения негативных отзывов и записи их в таблицу"""
    soup = await get_soup(url_top, proxy=False)
    if not soup:
        return

    # Рейтинг: берём первый <span> внутри .dashboard__grade-total-wrapper
    # (там лежит только число "4,2"), а не .text всего блока,
    # который содержит "4,2\nОчень хорошо\n87 отзывов"
    grade_wrapper = soup.find('div', {'class': 'dashboard__grade-total-wrapper'})
    if grade_wrapper:
        total_rating_raw = grade_wrapper.find('span').text.strip()
    else:
        # fallback: вытащить число регуляркой из всего блока
        block_text = soup.find('div', {'class': 'dashboard__grade-total'}).text
        m = re.search(r'[\d]+[,.][\d]+', block_text)
        total_rating_raw = m.group(0) if m else '0'
    print(f'[dreamjob] total_rating raw: {repr(total_rating_raw)}')
    total_rating = float(total_rating_raw.replace(',', '.'))
    print(f'[dreamjob] total_rating: {total_rating}')

    try:
        # Кол-во отзывов берём из вкладки Отзывы (a#tab_reviews),
        # т.к. на странице несколько span.tabs__count (вакансии, зарплаты и т.д.)
        tab_reviews = soup.find('a', {'id': 'tab_reviews'})
        total_reviews_content = tab_reviews.find('span', {'class': 'tabs__count'}).text
        print(f'[dreamjob] total_reviews raw: {repr(total_reviews_content)}')
        total_reviews = int(total_reviews_content.replace(' ', '').replace('\xa0', ''))
        print(f'[dreamjob] total_reviews: {total_reviews}')

    except Exception:
        total_reviews_content = soup.find('span', {'class': 'dashboard__grade-reviews'}).text
        total_reviews_split = total_reviews_content.split(' ')[0]
        print(f'[dreamjob] total_reviews fallback: {repr(total_reviews_split)}')
        total_reviews = int(total_reviews_split.replace(' ', '').replace('\xa0', ''))
        print(f'[dreamjob] total_reviews: {total_reviews}')

    employerId = url_top.split('/')[-1]

    for page in range(last_page, 1000):
        print(f'\nPage: {page}')

        url = f'https://dreamjob.ru/employers/{employerId}?nrs%5Bsort%5D=&nrs%5Bcities%5D=%5B%5D&nrs%5Bvacancies%5D=%5B%5D&nrs%5Bdepartments%5D=%5B%5D&nrs%5Bratings%5D=%5B%222%22%2C%221%22%5D&nrs%5Bfirst_selected%5D=ratings&nrs%5Btopics%5D%5B0%5D=%5B%5D&nrs%5Btopics%5D%5B1%5D=%5B%5D&page={page}&_pjax=%23data_pjax'
        print(url)
        soup_2 = await get_soup(url, proxy=False)
        if not soup_2:
            continue

        blocks = soup_2.find_all('div', {"class": 'review', 'data-partly': 'short'})

        len_b = len(blocks)

        print('Len:', len(blocks))
        if len_b == 0:
            return None

        datas = await empty_data()

        for block in blocks:
            try:
                date = block.find_next('div', {'class': 'review__header-date'}).text
            except:
                date_content = block.find_all('div', {'class': 'tags__item'})[1].text
                data_split = date_content.split(',')[-1]
                date = data_split.strip()

            date_content = date.split('\xa0')
            year = date_content[-1]
            month = months[date_content[-2]]

            if month < 10:
                month = f"0{month}"
            else:
                month = str(month)

            formatted_date = f"01.{month}.{year}"
            print(formatted_date)

            feedback = await extract_review_text(block)

            portal = 'dreamjob.ru'

            url_answer = block.find('a', {'class': 'bt bt--32 bt--primary-link icon-copy'}).get('href')
            if not url_answer:
                url_answer = block.find('a', role='button', tabindex='0').get('href')

            if not url_answer:
                url_answer = block.find('a', tabindex='0').get('href')

            if url_answer in links:
                continue

            author = block.find('h2', {'class': 'review__header-title'}).text.strip()

            rating_elem = block.find(
                lambda tag: tag.name == "div" and "class" in tag.attrs and "data-partly-switch" in tag.attrs)
            rating = float(rating_elem.text.strip().replace(',', '.')) if rating_elem else 0.0

            if rating > rating_max:
                continue

            datas['Дата'].append(formatted_date)
            datas['Текст'].append(feedback)
            datas['Бренд'].append(project)
            datas['Источник'].append(portal)
            datas['Url'].append(url_answer)
            datas['Автор'].append(author)
            datas['Оценка'].append(rating)
            datas['Общий Url'].append(url_top)
            datas['Кол-во отзывов'].append(total_reviews)
            datas['Оценка компании до удаления'].append(total_rating)

        await append_data_to_sheet_scopes(service, ss_id, project, datas)
        print('White datas - OK!')
        await asyncio.sleep(5)

        if len_b < 49:
            return

        await append_data_to_sheet_cell(service, ss_id, "links", "last_page", idx_last_page + 2, page)


async def pars_2gis(service, url, ss_id, project, links, rating_max):
    source = '2gis.ru'
    api_key = '6e7e1929-4ea9-4a5d-8c05-d601860389bd'

    try:
        org_id = await get_id_obj(url)
        if not org_id:
            print(f"2GIS: org_id not found in url: {url}")
            return

        # Собираем ВСЕ отрицательные отзывы через API (пагинация по 50)
        blocks = []
        branch_rating = 0
        branch_reviews_count = 0
        offset = 0

        while True:
            api_url = (
                f'https://public-api.reviews.2gis.com/3.0/branches/{org_id}/reviews'
                f'?limit=50&offset={offset}&ratings=negative&is_advertiser=false'
                f'&fields=meta.providers,meta.branch_rating,meta.branch_reviews_count,meta.total_count,'
                f'reviews.hiding_reason,reviews.emojis,reviews.trust_factors'
                f'&rated=true&sort_by=trust&key={api_key}&locale=ru_RU'
            )
            print(f"2GIS API URL: {api_url}")

            r_json = await get_soup_curl_cffi(api_url, dict_type=True, proxy=False)
            if not r_json:
                print(f"2GIS: API returned empty on offset={offset}")
                break

            meta = r_json.get('meta', {})
            branch_rating = meta.get('branch_rating', branch_rating)
            branch_reviews_count = meta.get('branch_reviews_count', branch_reviews_count)
            total_count = meta.get('total_count', 0)

            page_blocks = r_json.get('reviews', [])
            blocks.extend(page_blocks)
            print(f"2GIS: fetched {len(page_blocks)} reviews (offset={offset}, total_negative={total_count})")

            if len(page_blocks) < 50:
                break
            offset += 50

        print(f"2GIS: total blocks={len(blocks)} rating={branch_rating} reviews_count={branch_reviews_count}")

        existing_urls: set[str] = set()
        existing_rows: set[str] = set()
        try:
            df_existing = await read_table_id(service, ss_id, project)
            if df_existing is not None and not df_existing.empty:
                for col in ("Url", "URL", "url"):
                    if col in df_existing.columns:
                        existing_urls.update(
                            u for u in df_existing[col].astype(str).tolist()
                            if u and u != "nan"
                        )
                        break

                need_cols = ("Дата", "Автор", "Текст", "Оценка")
                if all(c in df_existing.columns for c in need_cols):
                    for _, r in df_existing[list(need_cols)].iterrows():
                        d = "" if pd.isna(r["Дата"]) else str(r["Дата"])
                        a = "" if pd.isna(r["Автор"]) else str(r["Автор"])
                        t = "" if pd.isna(r["Текст"]) else str(r["Текст"])
                        o = "" if pd.isna(r["Оценка"]) else str(r["Оценка"])
                        existing_rows.add(f"{d}|{a}|{t}|{o}")

        except Exception as ex:
            print(f"2GIS: dedup read error: {ex}")

        links_set = set(links or [])
        links_set.update(existing_urls)
        seen_rows = set(existing_rows)

        datas = await empty_data()

        for block in blocks:
            user_id = block['id']
            url_answer = f"https://2gis.ru/firm/{org_id}/tab/review/{user_id}"

            if url_answer in links_set:
                print('Такой комментарий уже есть в списке')
                continue

            rating = block['rating']
            if rating_max and rating > rating_max:
                continue

            date_content = block['date_created']
            date = datetime.strptime(date_content, "%Y-%m-%dT%H:%M:%S.%f%z")
            formatted_date = date.strftime("%d.%m.%Y")

            feedback = block['text']
            author = block['user']['name']

            row_id = f"{formatted_date}|{author}|{feedback}|{rating}"
            if row_id in seen_rows:
                continue
            seen_rows.add(row_id)

            links_set.add(url_answer)
            datas['Дата'].append(formatted_date)
            datas['Текст'].append(feedback)
            datas["Бренд"].append(project)
            datas["Источник"].append(source)
            datas['Url'].append(url_answer)
            datas['Автор'].append(author)
            datas['Оценка'].append(rating)
            datas["Общий Url"].append(url)
            datas["Кол-во отзывов"].append(branch_reviews_count)
            datas["Оценка компании до удаления"].append(branch_rating)

        if datas['Url']:
            await append_data_to_sheet_scopes(service, ss_id, project, datas)
            print(f"2GIS: wrote {len(datas['Url'])} rows")
            try:
                links.extend([u for u in datas['Url'] if u])
            except Exception:
                pass
        else:
            print("2GIS: nothing new to write")

        return 'OK!'

    except Exception as ex:
        print(f"2GIS: error: {ex}")
        return None


async def pars_zoon(service, url, ss_id, project, links, rating_max):
    """Парсер zoon.ru (Playwright)."""
    source = 'zoon.ru'
    await _ensure_hpo()

    p = browser = context = page = None
    try:
        p, browser, context, page = await get_playwright(headless=headless, proxy=proxy_on,
                                                         blocked_resource=False, stealth=True)

        content = await zoon_blocks(page, url, rating_max)
        if not content.get('Дата'):
            print('zoon: нет новых отзывов')
            return

        # Число отзывов и рейтинг компании — со страницы
        number_reviews = 0
        rating_before = 0.0
        counter_found = False
        try:
            counter = page.locator('div[data-uitest="count_reviews_in_total"]')
            if await counter.count() > 0:
                counter_found = True
                number_reviews = int((await counter.first.inner_text()).split(' ')[0])
            else:
                tabs = page.locator('span[class="service-block-nav-item-count z-text--13"]')
                if await tabs.count() > 1:
                    counter_found = True
                    number_reviews = int((await tabs.nth(1).inner_text()).replace(' ', '').replace('\xa0', ''))
        except Exception as ex:
            print(f'zoon: number_reviews error: {ex}')

        if number_reviews == 0 and counter_found:
            print('zoon: 0 отзывов')
            return

        try:
            rating_el = page.locator('div[data-target="rating-total"]')
            if await rating_el.count() > 0:
                rating_before = float((await rating_el.first.inner_text()).replace(',', '.'))
        except Exception as ex:
            print(f'zoon: rating error: {ex}')

        datas = await empty_data()

        for i in range(len(content['Дата'])):
            url_answer = content['Url'][i]
            if url_answer in links:
                print('Такой комментарий уже есть в списке')
                continue

            rating = content['Оценка'][i]
            if rating > rating_max:
                continue

            datas['Дата'].append(content['Дата'][i])
            datas['Текст'].append(content['Текст'][i])
            datas['Бренд'].append(project)
            datas['Источник'].append(source)
            datas['Url'].append(url_answer)
            datas['Автор'].append(content['Автор'][i])
            datas['Оценка'].append(rating)
            datas['Общий Url'].append(url)
            datas['Кол-во отзывов'].append(number_reviews)
            datas['Оценка компании до удаления'].append(rating_before)

        await append_data_to_sheet_scopes(service, ss_id, project, datas)

    finally:
        await close_playwright(p, browser, context, page)


async def pars_otzyvru(service, url, ss_id, project, links, rating_max):
    """Парсер otzyvru.com (Playwright + bs4 для текста отзыва)."""
    source = 'otzyvru.com'
    await _ensure_hpo()

    number_reviews = 74
    rating_before = 3.9

    p = browser = context = page = None
    try:
        p, browser, context, page = await get_playwright(headless=headless, proxy=proxy_on,
                                                         blocked_resource=False, stealth=True)

        page_num = 1
        while True:
            link = f'{url}?sort=rating_asc&page={page_num}'
            blocks = await blocks_otzovru(page, link)

            if len(blocks) == 0:
                return

            for block in blocks:
                url_answer = block['url']
                if not url_answer or url_answer in links:
                    continue

                try:
                    rating = int(block['rating'])
                except (TypeError, ValueError):
                    print('otzyvru: пропуск — рейтинг не найден')
                    continue

                print('rating:', rating)

                if rating > rating_max:
                    print('Rating is END!')
                    return

                author = block['author']

                try:
                    date = datetime.strptime(block['date'], "%Y-%m-%d")
                    formatted_date = date.strftime("%d.%m.%Y")
                except (TypeError, ValueError):
                    print('otzyvru: пропуск — дата не найдена')
                    continue

                feedback = await get_feedback_otzovru(url_answer)

                datas = await empty_data()

                datas['Дата'].append(formatted_date)
                datas['Текст'].append(feedback)
                datas['Бренд'].append(project)
                datas['Источник'].append(source)
                datas['Url'].append(url_answer)
                datas['Автор'].append(author)
                datas['Оценка'].append(rating)
                datas['Общий Url'].append(url)
                datas['Кол-во отзывов'].append(number_reviews)
                datas['Оценка компании до удаления'].append(rating_before)

                await append_data_to_sheet_scopes(service, ss_id, project, datas)
                await asyncio.sleep(1)

            page_num += 1

    finally:
        await close_playwright(p, browser, context, page)


async def get_feedback_irec(url, proxy_on, proxy_type):
    print('>>> Get feedback')
    html = await get_playwright_irec(url, proxy=proxy_on, proxy_type=proxy_type)
    soup = await get_soup_bs4(html, only_pars=True)

    # Если суп не сварился (Cloudflare заблокировал запрос и вернул 521/403)
    if not soup:
        print(f"Ошибка загрузки страницы (возможно блокировка): {url}")
        return ""

    # 1. Цепляемся за главный уникальный блок отзыва, как вы и предложили
    main_review_block = soup.find(attrs={"itemprop": "review"})

    # Если блок не найден (например, удалили отзыв или выдало капчу)
    if not main_review_block:
        print(f"Блок отзыва не найден на странице: {url}")
        return ""

    # 2. Ищем основной текст ВНУТРИ главного блока
    review_text = ""
    body_elem = main_review_block.find(attrs={"itemprop": "reviewBody"})

    if body_elem:
        # Удаляем мусорные блоки с картинками, чтобы их скрытый текст не попал в результат
        for img in body_elem.find_all('div', class_='inline-image'):
            img.extract()

        # Извлекаем текст, заменяя теги <br> и <p> на переносы строк
        review_text = body_elem.get_text(separator='\n', strip=True)

    # 3. Ищем достоинства (плюсы) ВНУТРИ главного блока
    pros_text = ""
    pros_elem = main_review_block.find(attrs={"itemprop": "positiveNotes"})
    if pros_elem:
        pros = [item.get_text(strip=True) for item in pros_elem.find_all(attrs={"itemprop": "name"})]
        pros_text = ", ".join(pros)

    # 4. Ищем недостатки (минусы) ВНУТРИ главного блока
    cons_text = ""
    cons_elem = main_review_block.find(attrs={"itemprop": "negativeNotes"})
    if cons_elem:
        cons = [item.get_text(strip=True) for item in cons_elem.find_all(attrs={"itemprop": "name"})]
        cons_text = ", ".join(cons)

    # 5. Собираем всё в красивый единый текст
    final_parts = []

    if review_text:
        final_parts.append(review_text)

    if pros_text:
        final_parts.append(f"Достоинства:\n{pros_text}")

    if cons_text:
        final_parts.append(f"Недостатки:\n{cons_text}")

    # Склеиваем всё с двойным отступом для красоты
    return "\n\n".join(final_parts)


async def pars_irec(service, url, ss_id, project, rating_max, links):
    """Парсер irecommend.ru (Playwright + bs4)."""
    proxy_on_irec = False
    proxy_type = 'mobile'

    source = 'irecommend.ru'

    site_page = 1

    while True:
        link = url + f'?page={site_page}&ft[r]=0'  # Только отрицательные
        print(f'\n******************* {site_page} ********************')

        html = await get_playwright_irec(link, proxy=proxy_on_irec, proxy_type=proxy_type)
        soup = await get_soup_bs4(html, only_pars=True)

        if not soup:
            print(f"Error: Could not retrieve soup for {link}")
            return

        blocks = soup.select('li[class^="item"]')
        len_b = len(blocks)
        print(f'Blocks = {len_b}')

        num_elem = soup.select_one('span.count[itemprop="reviewCount"]')
        number_reviews = num_elem.text.strip() if num_elem else "0"

        rating_elem = soup.select_one('span.rating[itemprop="ratingValue"]')
        rating_before = rating_elem.text.strip() if rating_elem else "0.0"

        for block in blocks:
            link_elem = block.select_one('a.reviewTextSnippet')
            if not link_elem:
                continue
            review_link = "https://irecommend.ru" + link_elem.get('href')

            if review_link in links:
                continue

            date_elem = block.select_one('div.created')
            formatted_date = date_elem.text.strip() if date_elem else ""

            stars = block.select('.starsRating .on')
            rating = len(stars)

            if rating_max < rating:
                continue

            mini_block = block.select_one('div.authorName')
            if not mini_block:
                continue

            author_a = mini_block.select_one('a')
            if not author_a:
                continue

            author = author_a.text.strip()
            author_link = "https://irecommend.ru" + author_a.get('href')

            review_text = await get_feedback_irec(review_link, proxy_on_irec, proxy_type)
            print(f'Text: {review_text}')

            datas = await empty_data()

            datas['Дата'].append(formatted_date)
            datas['Текст'].append(review_text)
            datas["Бренд"].append(project)
            datas["Источник"].append(source)

            datas['Url'].append(review_link)
            datas['Автор'].append(author)
            datas['Оценка'].append(rating)

            datas["Общий Url"].append(url)
            datas["Кол-во отзывов"].append(number_reviews)
            datas["Оценка компании до удаления"].append(rating_before)

            await append_data_to_sheet_scopes(service, ss_id, project, datas)
            await asyncio.sleep(5)
            print(f'--- append {author}')

        site_page += 1

        if len_b < 50:
            return


async def pars_tripadvisor(service, url, ss_id, project, links, rating_max):
    """Парсер tripadvisor.ru (Playwright)."""
    source = 'tripadvisor.ru'
    await _ensure_hpo()

    number_reviews = None
    rating_before = None

    p = browser = context = page = None
    try:
        p, browser, context, page = await get_playwright(headless=headless, proxy=proxy_on,
                                                         blocked_resource=False, stealth=True)

        # Пагинация: tripadvisor использует -oN- в URL (N = смещение, страницы по 10)
        for i in range(1, 55):
            print(f"----------------page-{i}----------------------")

            page_url = url
            if i > 1 and 'Reviews' in url:
                base = url.split('Reviews', 1)[0] + 'Reviews'
                suffix = re.sub(r'-o\d+', '', url.split('Reviews', 1)[1])
                page_url = f"{base}-o{(i - 1) * 10}{suffix}"

            blocks = await blocks_tripadvisor(page, page_url)

            if not blocks:
                break

            if i == 1:
                # Число отзывов и рейтинг компании (опционально)
                try:
                    rc = page.locator('div[data-automation="bubbleReviewCount"]')
                    if await rc.count() > 0:
                        txt = (await rc.first.inner_text()).replace('\xa0', ' ')
                        m = re.search(r'\d[\d\s]*', txt)
                        if m:
                            number_reviews = int(m.group(0).replace(' ', ''))
                except Exception as ex:
                    print(f'tripadvisor: number_reviews error: {ex}')

                try:
                    rv = page.locator('div[data-automation="bubbleRatingValue"]')
                    if await rv.count() > 0:
                        txt = (await rv.first.inner_text()).strip()
                        m = re.search(r'\d+[.,]\d+', txt)
                        if m:
                            rating_before = float(m.group(0).replace(',', '.'))
                except Exception as ex:
                    print(f'tripadvisor: rating error: {ex}')

            datas = await empty_data()

            for block in blocks:
                url_answer = block['url_answer']
                if not url_answer or url_answer in links:
                    continue

                formatted_date = block['formatted_date']
                feedback = block['feedback']
                author = block['author']
                rating = block['rating']

                datas['Дата'].append(formatted_date)
                datas['Текст'].append(feedback)
                datas['Бренд'].append(project)
                datas['Источник'].append(source)
                datas['Url'].append(url_answer)
                datas['Автор'].append(author)
                datas['Оценка'].append(rating)
                datas['Общий Url'].append(url)
                datas['Кол-во отзывов'].append(number_reviews)
                datas['Оценка компании до удаления'].append(rating_before)

            await append_data_to_sheet_scopes(service, ss_id, project, datas)
            await asyncio.sleep(3)

    finally:
        await close_playwright(p, browser, context, page)


async def close_playwright(p=None, browser=None, context=None, page=None):
    """Универсальная функция для корректного закрытия всех объектов Playwright.

    Закрывает page -> context -> browser -> останавливает playwright.
    Каждый шаг обёрнут в try/except, чтобы ошибка на одном этапе
    не прерывала закрытие остальных.
    """
    try:
        if page is not None:
            await page.close()
    except Exception:
        pass
    try:
        if context is not None:
            await context.close()
    except Exception:
        pass
    try:
        if browser is not None:
            await browser.close()
    except Exception:
        pass
    try:
        if p is not None:
            await p.stop()
    except Exception:
        pass


async def pars_otzovik(service, url, ss_id, project, ratio, links):
    """Парсер otzovik.com (Playwright)."""
    proxy_on_otz = False
    await _ensure_hpo()

    p = browser = context = page = None
    p_2 = browser_2 = context_2 = page_2 = None
    try:
        p, browser, context, page = await get_playwright(headless=headless,
                                                         proxy=proxy_on_otz,
                                                         proxy_type='ru',
                                                         stealth=True,
                                                         blocked_resource=False)

        p_2, browser_2, context_2, page_2 = await get_playwright(headless=headless,
                                                                 proxy=proxy_on_otz,
                                                                 proxy_type='ru',
                                                                 stealth=True,
                                                                 blocked_resource=False)

        source = 'otzovik.com'

        for rt in range(1, ratio + 1):
            st_page = 1
            print(f'[otzovik] Начинаем рейтинг={rt}, страница={st_page}')
            while True:
                url_full = f'{url}{st_page}/?ratio={rt}'
                print(f'[otzovik] Переход: {url_full}')

                await page.goto(url_full)
                status = await check_captcha(page)

                # Собираем ВСЕ карточки отзывов — класс statusN динамический,
                # поэтому выбираем только по общим признакам: div.item.mshow0
                review_cards = await page.query_selector_all('div.item.mshow0')
                len_cards = len(review_cards)
                print(f'[otzovik] ratio={rt}, страница={st_page}: найдено карточек = {len_cards}')

                for card in review_cards:
                    # --- Сбор данных с основной страницы (page) ---
                    # Дата отзыва
                    date_el = await card.query_selector('.review-postdate span')
                    date_str = await date_el.inner_text() if date_el else None
                    formatted_date = await date_convert(date_str)

                    # Оценка
                    rating_el = await card.query_selector('.rating-score span')
                    rating = await rating_el.inner_text() if rating_el else None

                    if rating is None:
                        print(f'[otzovik] Пропуск карточки — оценка не найдена')
                        continue

                    if int(rating) > int(ratio):
                        continue

                    # Ссылка на отзыв
                    link_el = await card.query_selector('a.review-title')
                    review_link = ""
                    if link_el:
                        review_link = "https://otzovik.com" + await link_el.get_attribute('href')

                    if review_link in links:
                        continue

                    # Автор и ссылка на автора
                    author_el = await card.query_selector('a.user-login')
                    author_name = ""
                    if author_el:
                        author_name = (await author_el.inner_text()).strip()

                    feedback = await get_feedback(page_2, review_link)

                    datas = await empty_data()

                    datas['Дата'].append(formatted_date)
                    datas['Текст'].append(feedback)
                    datas["Бренд"].append(project)
                    datas["Источник"].append(source)

                    datas['Url'].append(review_link)
                    datas['Автор'].append(author_name)
                    datas['Оценка'].append(rating)

                    datas["Общий Url"].append(url)
                    datas["Кол-во отзывов"].append(485)
                    datas["Оценка компании до удаления"].append(4.4)

                    await append_data_to_sheet_scopes(service, ss_id, project, datas)

                print(f'[otzovik] Страница {st_page} обработана. Карточек: {len_cards}. '
                      f'{"Последняя страница — выход." if len_cards < 40 else "Переходим дальше."}')

                if len_cards < 40:
                    break

                st_page += 1

    finally:
        await close_playwright(p, browser, context, page)
        await close_playwright(p_2, browser_2, context_2, page_2)


async def pars_pravda(service, url, ss_id, project, links):
    """Парсер pravda-sotrudnikov.ru (bs4)."""
    source = 'pravda-sotrudnikov.ru'
    rating = None

    soup = await get_soup(url, proxy=False)

    number_reviews = soup.find('span', {'class': 'company-reviews-title-quantity'}).text
    print(number_reviews)

    rating_before = soup.find('div', {'class': 'company-info-contacts-row'}).find(
        'span', {'class': "rating-autostars"}).get('data-rating')
    print(rating_before)

    last_page = 1
    li = soup.find_all('li')
    for l in li:
        txt = l.text
        if txt.isdigit():
            last_page = int(txt)

    print(f'Last page: {last_page}')

    for i in range(last_page):
        url_page = url + f'?page={i + 1}'
        print(url_page)

        blocks = await blocks_pravda(url_page)
        print(f'LenB: {len(blocks)}')

        if len(blocks) > 0:
            for block in blocks:

                yellow_button = block.find('a', class_='btn btn-yellow show-answers-button')
                url_answer = 'https://pravda-sotrudnikov.ru' + yellow_button.get('href')
                if url_answer in links:
                    continue

                date_str = block.find('div', class_='company-reviews-list-item-date').text.strip()
                date = datetime.strptime(date_str, "%H:%M %d.%m.%Y")
                formatted_date = date.strftime("%d.%m.%Y")

                author = block.find('div', class_='company-reviews-list-item-name').text
                author = " ".join(author.split())

                text = block.find('div', {'class': 'row'}).text
                feedback = "\n".join(line.strip() for line in text.splitlines() if line.strip())

                datas = await empty_data()

                datas['Дата'].append(formatted_date)
                datas['Текст'].append(feedback)
                datas['Бренд'].append(project)
                datas['Источник'].append(source)
                datas['Url'].append(url_answer)
                datas['Автор'].append(author)
                datas['Оценка'].append(rating)
                datas['Общий Url'].append(url)
                datas['Кол-во отзывов'].append(number_reviews)
                datas['Оценка компании до удаления'].append(rating_before)

                await append_data_to_sheet_scopes(service, ss_id, project, datas)
                await asyncio.sleep(1)


async def blocks_ya_maps(service, page, url, ss_id, project, links, rating_max):
    source = "yandex.ru/maps"
    # Yandex Maps часто грузится долго и может не дождаться события "load".
    # Используем domcontentloaded + увеличенный timeout.
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=120_000)

    except Exception as ex:
        print(f"--- goto timeout/err: {ex}. retry...")
        await page.goto(url, wait_until="domcontentloaded", timeout=180_000)

    current_url = page.url

    url = await get_base_url(current_url)
    full_url = url
    if 'reviews' not in url:
        full_url = os.path.join(url, 'reviews')

    print(f"full_url1: {full_url}")
    await asyncio.sleep(3)

    if 'showcaptcha' in full_url:
        print('YA: captcha detected, reload...')
        await page.reload()
        current_url = page.url
        url = await get_base_url(current_url)
        full_url = url
        if 'reviews' not in url:
            full_url = os.path.join(url, 'reviews')

    print(f"full_url2: {full_url}")
    try:
        await page.goto(full_url, wait_until="domcontentloaded", timeout=120_000)
    except Exception as ex:
        print(f"--- goto(full_url) timeout/err: {ex}. retry...")
        await page.goto(full_url, wait_until="domcontentloaded", timeout=180_000)

    # Общее число отзывов и рейтинг компании — только из ratingData (НЕ reviewResults).
    # Список reviewResults в state-view всегда ~50 и при скролле не растёт.
    rating_score, review_count, rating_count = None, 0, 0
    try:
        state_view = await page.locator('script.state-view').first.inner_text()
        json_state = json.loads(state_view)
        rating_score, review_count, rating_count = await get_rrr(json_state)
    except Exception as ex:
        print(f"YA: ratingData from state-view failed: {ex}")

    if not review_count:
        try:
            tab_text = await page.locator('div.tabs-select-view__title._name_reviews').first.inner_text(timeout=5000)
            m = re.search(r'(\d+)', tab_text.replace('\xa0', ' '))
            if m:
                review_count = int(m.group(1))
        except Exception:
            pass

    if not review_count:
        return {}

    # ---------------------------------------------------------------------
    # ДЕДУП ПО УЖЕ СУЩЕСТВУЮЩИМ ДАННЫМ В ТАБЛИЦЕ
    # ---------------------------------------------------------------------
    existing_urls: set[str] = set()
    existing_rows: set[str] = set()
    try:
        df_existing = await read_table_id(service, ss_id, project)
        if df_existing is not None and not df_existing.empty:
            for col in ("Url", "URL", "url"):
                if col in df_existing.columns:
                    existing_urls.update(
                        u for u in df_existing[col].astype(str).tolist()
                        if u and u != "nan"
                    )
                    break

            need_cols = ("Дата", "Автор", "Текст", "Оценка")
            if all(c in df_existing.columns for c in need_cols):
                for _, r in df_existing[list(need_cols)].iterrows():
                    d = "" if pd.isna(r["Дата"]) else str(r["Дата"])
                    a = "" if pd.isna(r["Автор"]) else str(r["Автор"])
                    t = "" if pd.isna(r["Текст"]) else str(r["Текст"])
                    o = "" if pd.isna(r["Оценка"]) else str(r["Оценка"])
                    existing_rows.add(f"{d}|{a}|{t}|{o}")
    except Exception as ex:
        print(f"YA: could not read existing sheet for dedup: {ex}")

    async def extract_cards_batch(start_idx: int):
        """Быстро читаем только новые карточки из DOM одним JS-вызовом."""
        return await page.evaluate(
            """(startIdx) => {
                const cards = document.querySelectorAll('div.business-reviews-card-view__review');
                return Array.from(cards).slice(startIdx).map(card => {
                    const textEl = card.querySelector('span.spoiler-view__text-container');
                    const authorEl = card.querySelector('span[itemprop="name"]')
                        || card.querySelector('span[dir="auto"]');
                    const dateEl = card.querySelector('meta[itemprop="datePublished"]');
                    const ratingEl = card.querySelector('meta[itemprop="ratingValue"]');
                    const stars = card.querySelectorAll('span.business-rating-badge-view__star._full');
                    const linkEl = card.querySelector('a.business-review-view__user-icon');
                    const href = linkEl ? linkEl.getAttribute('href') : '';
                    return {
                        text: textEl ? textEl.innerText.trim() : '',
                        author: authorEl ? authorEl.innerText.trim() : '',
                        date: dateEl ? dateEl.content : '',
                        rating: ratingEl ? ratingEl.content : String(stars.length || ''),
                        publicId: href ? href.split('/').pop() : 'NoLink',
                    };
                });
            }""",
            start_idx,
        )

    links_set = set(links or [])
    links_set.update(existing_urls)
    seen_rows = set(existing_rows)
    total_written = 0
    processed_count = 0

    cards = page.locator('div.business-reviews-card-view__review')
    prev_found = -1
    unchanged = 0

    async def write_new_batch(found: int, scroll_i: int):
        nonlocal processed_count, total_written
        if found <= processed_count:
            return 0

        batch = await extract_cards_batch(processed_count)
        if not batch:
            processed_count = found
            return 0

        datas = await empty_data()
        for item in batch:
            feedback = item.get('text') or ''
            author = item.get('author') or ''

            rating = None
            raw_rating = item.get('rating')
            if raw_rating not in (None, ''):
                try:
                    rating = int(float(raw_rating))
                except Exception:
                    rating = None

            if rating_max and rating is not None and rating > rating_max:
                continue

            formatted_date = ""
            date_content = item.get('date') or ''
            if date_content:
                try:
                    dt = datetime.strptime(date_content, "%Y-%m-%dT%H:%M:%S.%fZ")
                    formatted_date = dt.strftime("%d.%m.%Y")
                except Exception:
                    pass

            row_id = f"{formatted_date}|{author}|{feedback}|{rating}"
            if row_id in seen_rows:
                continue
            seen_rows.add(row_id)

            public_id = item.get('publicId') or 'NoLink'
            review_link = f"{full_url}?reviews%5BpublicId%5D={public_id}&utm_source=review"

            if review_link in links_set:
                continue

            links_set.add(review_link)
            datas['Дата'].append(formatted_date)
            datas['Текст'].append(feedback)
            datas['Бренд'].append(project)
            datas['Источник'].append(source)
            datas['Url'].append(review_link)
            datas['Автор'].append(author)
            datas['Оценка'].append(rating)
            datas['Общий Url'].append(url)
            datas['Кол-во отзывов'].append(review_count)
            datas['Оценка компании до удаления'].append(rating_score)

        start_idx = processed_count
        written = len(datas['Url'])
        processed_count = found
        if written:
            await append_data_to_sheet_scopes(service, ss_id, project, datas)
            total_written += written
            try:
                links.extend([u for u in datas['Url'] if u])
            except Exception:
                pass

        print(
            f"YA batch scroll {scroll_i}: cards {start_idx}-{found} "
            f"new={len(batch)} wrote={written} total_written={total_written}"
        )
        return written

    # Скролл + инкрементальная запись после каждой догрузки
    for i in range(5000):
        found = await cards.count()
        print(f"YA scroll {i}: found={found} total={review_count} unchanged={unchanged}")

        await write_new_batch(found, i)

        if found >= review_count:
            break

        if found == prev_found:
            unchanged += 1
        else:
            unchanged = 0
            prev_found = found

        if unchanged >= 10:
            break

        if found > 0:
            try:
                last_card = cards.nth(found - 1)
                await last_card.scroll_into_view_if_needed(timeout=5000)
                try:
                    await last_card.hover(timeout=1000)
                except Exception:
                    pass
            except Exception:
                pass

        await page.mouse.wheel(0, 3500)
        await asyncio.sleep(1.2)

    final_found = await cards.count()
    await write_new_batch(final_found, -1)

    print(f"YA done: wrote {total_written} rows (found DOM={final_found} total={review_count})")

    return {
        "rating_score": rating_score,
        "review_count": review_count,
        "rating_count": rating_count,
        "items_found_dom": final_found,
        "items_written": total_written,
    }


async def _blocks_ya_maps_fetch_reviews(service, url, ss_id, project, links, rating_max,
                                        ranking='by_rating_asc', max_pages=None):
    """
    Парсинг отзывов Яндекс.Карт (org-страницы) через внутренний API fetchReviews.

    Страница сама вызывает fetchReviews при смене сортировки — перехватываем
    ответы через Playwright (токены csrf/s генерирует фронтенд, без браузера
    запросы отклоняются).

    :param ranking: сортировка:
        'by_time' — сначала новые («По новизне»);
        'by_rating_asc' — сначала низкие оценки («Сначала низкие»);
        'by_rating_desc' — сначала высокие («Сначала высокие»).
    :param max_pages: сколько страниц отзывов собрать (None — все, что догрузит скролл).
        Для частых запусков (несколько раз в день) достаточно max_pages=1.
    """
    source = "yandex.ru/maps"

    # Варианты названий пунктов сортировки (у разных организаций/регионов бывают разные)
    SORT_LABELS = {
        'by_time': ['По новизне', 'Сначала новые', 'Сначала новые отзывы'],
        'by_rating_asc': ['Сначала низкие', 'Сначала отрицательные'],
        'by_rating_desc': ['Сначала высокие', 'Сначала положительные'],
    }

    sort_labels = SORT_LABELS.get(ranking)
    if not sort_labels:
        print(f'YA fetchReviews: сортировка {ranking!r} не поддерживается')
        return {'error': f'Сортировка {ranking!r} не поддерживается'}

    p = browser = context = page = None
    try:
        p, browser, context, page = await get_playwright(headless=headless, proxy=proxy_on,
                                                         blocked_resource=False, stealth=True)

        api_responses = []

        def on_response(resp):
            if 'fetchReviews' in resp.url and f'ranking={ranking}' in resp.url:
                api_responses.append(resp)

        page.on('response', on_response)

        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=120_000)
        except Exception as ex:
            print(f'YA fetchReviews: goto error: {ex}')
            return {'error': f'Не удалось загрузить страницу: {ex}'}

        await asyncio.sleep(6)

        if 'showcaptcha' in page.url:
            return {'error': 'Яндекс показал капчу (showcaptcha) — повторите позже или смените IP'}

        # Закрываем возможные диалоги (вход/регион/подсказки) — их оверлей
        # перехватывает клики, из-за чего сортировка «не нажимается»
        for _ in range(3):
            try:
                await page.keyboard.press('Escape')
                await page.wait_for_timeout(700)
            except Exception:
                break
            close_btn = page.locator('button[class*="dialog__close"]').first
            if await close_btn.count() > 0:
                try:
                    if await close_btn.is_visible():
                        await close_btn.click(timeout=2000)
                except Exception:
                    pass
            else:
                break

        # Смена сортировки: контрол — div.rating-ranking-view (или текст «По умолчанию»)
        try:
            sort_btn = page.locator('div.rating-ranking-view').first
            if await sort_btn.count() == 0:
                sort_btn = page.get_by_text('По умолчанию', exact=False).first
            await sort_btn.scroll_into_view_if_needed(timeout=5000)
            await sort_btn.click(timeout=8000)
            await asyncio.sleep(1.5)

            clicked = False
            for label in sort_labels:
                try:
                    await page.get_by_text(label, exact=True).first.click(timeout=3000)
                    clicked = True
                    print(f'YA fetchReviews: сортировка -> {label}')
                    break
                except Exception:
                    try:
                        await page.locator(f'text={label}').first.click(timeout=2000)
                        clicked = True
                        print(f'YA fetchReviews: сортировка -> {label} (fuzzy)')
                        break
                    except Exception:
                        continue

            if not clicked:
                msg = (f'Не найден пункт сортировки {sort_labels} '
                       f'(возможна капча или требуется вход на Яндекс)')
                print(f'YA fetchReviews: {msg}')
                return {'error': msg}

        except Exception as ex:
            print(f'YA fetchReviews: не удалось сменить сортировку: {ex}')
            return {'error': f'Не удалось сменить сортировку: {ex}'}

        async def collect():
            """Достаёт отзывы из перехваченных ответов fetchReviews."""
            out, seen = [], set()
            total = 0
            for resp in api_responses:
                try:
                    data = await resp.json()
                except Exception:
                    continue
                params = (data.get('data') or {}).get('params') or {}
                total = max(total, params.get('count', 0) or 0)
                for rev in (data.get('data') or {}).get('reviews') or []:
                    rid = rev.get('reviewId')
                    if rid and rid not in seen:
                        seen.add(rid)
                        out.append(rev)
            return out, total

        # Ждём ответ fetchReviews (до ~20 сек)
        reviews, total_count = [], 0
        for _ in range(10):
            await asyncio.sleep(2)
            reviews, total_count = await collect()
            if reviews:
                break

        if not reviews:
            return {'error': 'Отзывы не получены (смотрите логи: возможна капча или вход на Яндекс)'}

        # Догрузка следующих страниц скроллом (если запрошено)
        pages_left = (max_pages - 1) if max_pages is not None else None
        while pages_left is None or pages_left > 0:
            before = len(reviews)
            await page.mouse.wheel(0, 8000)
            await asyncio.sleep(2.5)
            reviews, total_count = await collect()
            if len(reviews) == before:
                break
            if pages_left is not None:
                pages_left -= 1

        if not reviews:
            print('YA fetchReviews: отзывы не получены')
            return {'error': 'Отзывы не получены (смотрите логи: возможна капча или вход на Яндекс)'}

        print(f'YA fetchReviews: собрано отзывов = {len(reviews)}, всего у компании = {total_count}')

        # Рейтинг компании со страницы (опционально)
        company_rating = None
        try:
            els = page.locator('span.business-summary-rating-badge-view__rating-text')
            n = await els.count()
            if n:
                parts = []
                for i in range(min(n, 4)):
                    txt = await els.nth(i).inner_text()
                    parts.append(txt.strip())
                joined = ''.join(parts)
                m = re.search(r'\d+[.,]\d+', joined)
                if m:
                    company_rating = float(m.group(0).replace(',', '.'))
                else:
                    m2 = re.search(r'\d+', joined)
                    if m2:
                        company_rating = float(m2.group(0))
        except Exception as ex:
            print(f'YA fetchReviews: rating error: {ex}')

        # ---------------------------------------------------------------------
        # ДЕДУП ПО УЖЕ СУЩЕСТВУЮЩИМ ДАННЫМ В ТАБЛИЦЕ (если передан ss_id)
        # ---------------------------------------------------------------------
        existing_urls: set[str] = set()
        existing_rows: set[str] = set()
        if ss_id is not None:
            try:
                df_existing = await read_table_id(service, ss_id, project)
                if df_existing is not None and not df_existing.empty:
                    for col in ("Url", "URL", "url"):
                        if col in df_existing.columns:
                            existing_urls.update(
                                u for u in df_existing[col].astype(str).tolist()
                                if u and u != "nan"
                            )
                            break

                    need_cols = ("Дата", "Автор", "Текст", "Оценка")
                    if all(c in df_existing.columns for c in need_cols):
                        for _, r in df_existing[list(need_cols)].iterrows():
                            d = "" if pd.isna(r["Дата"]) else str(r["Дата"])
                            a = "" if pd.isna(r["Автор"]) else str(r["Автор"])
                            t = "" if pd.isna(r["Текст"]) else str(r["Текст"])
                            o = "" if pd.isna(r["Оценка"]) else str(r["Оценка"])
                            existing_rows.add(f"{d}|{a}|{t}|{o}")
            except Exception as ex:
                print(f"YA fetchReviews: could not read existing sheet for dedup: {ex}")

        links_set = set(links or [])
        links_set.update(existing_urls)
        seen_rows = set(existing_rows)

        base_url = await get_base_url(url)
        datas = await empty_data()

        for rev in reviews:
            rating = rev.get('rating')
            if rating is None or (rating_max and rating > rating_max):
                continue

            rid = rev.get('reviewId')
            review_link = f"{base_url}?reviews%5BpublicId%5D={rid}&utm_source=review"
            if review_link in links_set:
                continue
            links_set.add(review_link)

            feedback = rev.get('text') or ''
            author = (rev.get('author') or {}).get('name') or ''

            formatted_date = ""
            ts = rev.get('updatedTime')
            if ts:
                try:
                    dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ")
                    formatted_date = dt.strftime("%d.%m.%Y")
                except Exception:
                    pass

            row_id = f"{formatted_date}|{author}|{feedback}|{rating}"
            if row_id in seen_rows:
                continue
            seen_rows.add(row_id)

            datas['Дата'].append(formatted_date)
            datas['Текст'].append(feedback)
            datas['Бренд'].append(project)
            datas['Источник'].append(source)
            datas['Url'].append(review_link)
            datas['Автор'].append(author)
            datas['Оценка'].append(rating)
            datas['Общий Url'].append(base_url)
            datas['Кол-во отзывов'].append(total_count)
            datas['Оценка компании до удаления'].append(company_rating if company_rating is not None else '')

        if datas['Url']:
            if ss_id is not None:
                await append_data_to_sheet_scopes(service, ss_id, project, datas)
                print(f"YA fetchReviews: wrote {len(datas['Url'])} rows")
                try:
                    links.extend([u for u in datas['Url'] if u])
                except Exception:
                    pass
            else:
                print(f"YA fetchReviews: ss_id не задан — запись пропущена, строк: {len(datas['Url'])}")
        else:
            print("YA fetchReviews: nothing new to write")

        return {
            "rating_score": company_rating,
            "review_count": total_count,
            "items_written": len(datas['Url']),
            "datas": datas,
        }

    finally:
        await close_playwright(p, browser, context, page)


async def blocks_ya_reviews_api(service, url, ss_id, project, links, rating_max, ranking='by_rating_asc', max_pages=None):
    """
    Парсинг отзывов Яндекс (универсальная функция).

    - reviews.yandex.ru — скрытый API digest (без Playwright);
    - org-страницы Яндекс.Карт (yandex.ru/maps/org/...) — внутренний API fetchReviews
      через Playwright (перехват ответов при смене сортировки).

    :param ranking: сортировка:
        'by_rating_asc' — сначала отрицательные/низкие оценки;
        'by_time' — сначала свежие.
    :param max_pages: ограничение числа загружаемых страниц (None — все).
        Для частых запусков (несколько раз в день) достаточно max_pages=1.

    Если ss_id=None — запись в Google-таблицу и дедупликация пропускаются,
    функция только возвращает собранные данные.
    """
    if '/maps/org/' in url:
        return await _blocks_ya_maps_fetch_reviews(service, url, ss_id, project, links, rating_max,
                                                   ranking=ranking, max_pages=max_pages)

    from urllib.parse import quote
    source = "reviews.yandex.ru"

    try:
        # 1. HTML страницы: objectId + рейтинг компании
        html = await get_soup_curl_cffi(url, dict_type=False, proxy=False)
        if html is None:
            print(f"YA reviews: не удалось загрузить страницу: {url}")
            return {'error': f'Не удалось загрузить страницу: {url}'}

        html_text = str(html)
        m = re.search(r'"objectId":"([^"]+)"', html_text)
        if not m:
            print(f"YA reviews: objectId не найден на странице: {url}")
            return {'error': f'objectId не найден на странице: {url}'}
        object_id = m.group(1)
        otype = object_id.split('/')[1].capitalize() if '/' in object_id else 'Site'
        print(f"YA reviews: objectId={object_id} otype={otype}")

        # 2. Рейтинг компании из JSON-LD
        rating_score = None
        m_ld = re.search(r'<script type="application/ld\+json">(.*?)</script>', html_text, re.S)
        if m_ld:
            try:
                ld = json.loads(m_ld.group(1))
                rating_score = ld.get('aggregateRating', {}).get('ratingValue')
            except Exception:
                pass

        # 3. Дедуп по уже существующим данным в таблице (если передан ss_id)
        existing_urls: set[str] = set()
        existing_rows: set[str] = set()
        if ss_id is not None:
            try:
                df_existing = await read_table_id(service, ss_id, project)
                if df_existing is not None and not df_existing.empty:
                    for col in ("Url", "URL", "url"):
                        if col in df_existing.columns:
                            existing_urls.update(
                                u for u in df_existing[col].astype(str).tolist()
                                if u and u != "nan"
                            )
                            break

                    need_cols = ("Дата", "Автор", "Текст", "Оценка")
                    if all(c in df_existing.columns for c in need_cols):
                        for _, r in df_existing[list(need_cols)].iterrows():
                            d = "" if pd.isna(r["Дата"]) else str(r["Дата"])
                            a = "" if pd.isna(r["Автор"]) else str(r["Автор"])
                            t = "" if pd.isna(r["Текст"]) else str(r["Текст"])
                            o = "" if pd.isna(r["Оценка"]) else str(r["Оценка"])
                            existing_rows.add(f"{d}|{a}|{t}|{o}")
            except Exception as ex:
                print(f"YA reviews: could not read existing sheet for dedup: {ex}")

        links_set = set(links or [])
        links_set.update(existing_urls)
        seen_rows = set(existing_rows)

        datas = await empty_data()
        review_count = 0
        offset = 0
        page_num = 0

        while True:
            page_num += 1
            api_url = (
                'https://reviews.yandex.ru/ugcpub/digest'
                f'?notEscapeUserDisplayName=1'
                f'&ranking={ranking}'
                f'&fixTokens=true'
                f'&add_my_review=true'
                f'&objectId={quote(object_id)}&appId=vertical-object'
                f'&offset={offset}'
                f'&otype={otype}'
                f'&limit=50'
                f'&withNpsScore=1'
                f'&reviewsTypeId=0'
                f'&addComments=true'
                f'&isSiteShop=1'
                f'&ignore_filter_aspects_stats_by_tag=1'
            )
            r_json = await get_soup_curl_cffi(api_url, dict_type=True, proxy=False)
            if not r_json:
                print(f"YA reviews: API вернул пусто на offset={offset}")
                break

            review_count = r_json.get('pager', {}).get('totalCount', review_count)

            page_reviews = [
                v for v in r_json.get('view', {}).get('views', [])
                if v.get('type') == '/ugc/review'
            ]
            if not page_reviews:
                break

            # Стоп по рейтингу имеет смысл только при сортировке по рейтингу
            if ranking == 'by_rating_asc':
                if all(v.get('rating', {}).get('val', 0) > rating_max for v in page_reviews):
                    print(f"YA reviews: стоп на offset={offset} — все отзывы rating > {rating_max}")
                    break

            for item in page_reviews:
                rating = item.get('rating', {}).get('val')
                if rating is None or (rating_max and rating > rating_max):
                    continue

                feedback = item.get('text') or ''
                author = item.get('author', {}).get('name') or ''
                review_id = item.get('id') or 'NoLink'

                formatted_date = ""
                ts = item.get('time')
                if ts:
                    try:
                        formatted_date = datetime.fromtimestamp(ts / 1000).strftime("%d.%m.%Y")
                    except Exception:
                        pass

                row_id = f"{formatted_date}|{author}|{feedback}|{rating}"
                if row_id in seen_rows:
                    continue
                seen_rows.add(row_id)

                review_link = f"{url}?reviews%5BpublicId%5D={review_id}&utm_source=review"
                if review_link in links_set:
                    continue

                links_set.add(review_link)
                datas['Дата'].append(formatted_date)
                datas['Текст'].append(feedback)
                datas['Бренд'].append(project)
                datas['Источник'].append(source)
                datas['Url'].append(review_link)
                datas['Автор'].append(author)
                datas['Оценка'].append(rating)
                datas['Общий Url'].append(url)
                datas['Кол-во отзывов'].append(review_count)
                datas['Оценка компании до удаления'].append(rating_score)

            if len(page_reviews) < 25:
                break
            offset += 25
            if max_pages is not None and page_num >= max_pages:
                print(f"YA reviews: достигнут лимит страниц max_pages={max_pages}")
                break

        if datas['Url']:
            if ss_id is not None:
                await append_data_to_sheet_scopes(service, ss_id, project, datas)
                print(f"YA reviews: wrote {len(datas['Url'])} rows")
                try:
                    links.extend([u for u in datas['Url'] if u])
                except Exception:
                    pass
            else:
                print(f"YA reviews: ss_id не задан — запись пропущена, строк: {len(datas['Url'])}")
        else:
            print("YA reviews: nothing new to write")

        return {
            "rating_score": rating_score,
            "review_count": review_count,
            "items_written": len(datas['Url']),
            "datas": datas,
        }

    except Exception as ex:
        print(f"YA reviews: error: {ex}")
        return {'error': f'YA reviews: {ex}'}


async def pars_ya_maps(service, url, ss_id, project, links, rating_max, ranking='by_rating_asc', max_pages=None):
    """
    Yandex парсинг.

    reviews.yandex.ru — через скрытый API digest (без Playwright).
    yandex.ru/maps — через Playwright (legacy).

    `get_playwright` находится внутри `pars_ya_maps`, чтобы `multi_pars`
    не зависел от внешней переменной `page`.
    """
    await _ensure_hpo()

    if 'reviews.yandex.ru' in url:
        return await blocks_ya_reviews_api(service, url, ss_id, project, links, rating_max,
                                           ranking=ranking, max_pages=max_pages)

    # org-страницы Яндекс.Карт: сначала API fetchReviews, при неудаче — legacy скролл
    if '/maps/org/' in url:
        result = await blocks_ya_reviews_api(service, url, ss_id, project, links, rating_max,
                                             ranking=ranking, max_pages=max_pages)
        if result:
            return result
        print('YA: fetchReviews не дал данных — fallback на legacy blocks_ya_maps')

    p = browser = context = page = None
    try:
        p, browser, context, page = await get_playwright(headless=headless,
                                                         blocked_resource=False)
        await blocks_ya_maps(service, page, url, ss_id, project, links, rating_max)
        return 'OK!'

    finally:
        try:
            if page is not None:
                await page.close()
            if context is not None:
                await context.close()
            if browser is not None:
                await browser.close()
            if p is not None:
                await p.stop()
        except Exception:
            pass


async def multi_pars(ss_id, project):
    """
    Сбор отзывов по ссылкам из листа 'links' Google-таблицы.

    Для каждого портала вызывается свой парсер, статус пишется
    обратно в колонку 'status' ('OK!' или текст ошибки).
    """
    service = await get_service()

    df = await read_table_id(service, ss_id, 'links')
    print(df)

    if df.empty:
        return

    links = await get_links(service, ss_id, project)

    for k, row in df.iterrows():
        status = row['status']
        if status == 'OK!':
            continue

        url = row['link']
        print(f'\n{url}')
        rating_max = int(row['max_raiting'])
        try:
            last_page = int(row['last_page'])
        except:
            last_page = 0

        try:
            if 'otzovik' in url:
                await pars_otzovik(service, url, ss_id, project, rating_max, links)
                result = 'OK!'

            elif '2gis' in url:
                await pars_2gis(service, url, ss_id, project, links, rating_max)
                result = 'OK!'

            elif 'yandex' in url:
                await pars_ya_maps(service, url, ss_id, project, links, rating_max)
                result = 'OK!'

            elif 'zoon' in url:
                await pars_zoon(service, url, ss_id, project, links, rating_max)
                result = 'OK!'

            elif 'irecommend' in url:
                await pars_irec(service, url, ss_id, project, rating_max, links)
                result = 'OK!'

            elif 'tripadvisor' in url:
                await pars_tripadvisor(service, url, ss_id, project, links, rating_max)
                result = 'OK!'

            elif 'pravda-sotrudnikov' in url:
                await pars_pravda(service, url, ss_id, project, links)
                result = 'OK!'

            elif 'otzyvru' in url:
                await pars_otzyvru(service, url, ss_id, project, links, rating_max)
                result = 'OK!'

            elif 'dreamjob' in url:
                await pars_dreamjob(service, url, ss_id, project, links, rating_max, k, last_page)
                result = 'OK!'

            else:
                print(f'Неизвестный портал: {url}')
                result = f'Unknown portal: {url}'

        except Exception as Ex:
            print(f'ERROR multi_pars ({url}): {Ex}')
            result = f'ERROR: {Ex}'

        # Пишем статус: 'OK!' или текст ошибки (ошибочные строки будут переобработаны)
        await append_data_to_sheet_cell(service, ss_id, 'links', 'status', k + 2, str(result)[:100])
        await asyncio.sleep(3)

if "__main__" == __name__:
    from pprint import pprint

    async def main():
        service = await get_service()
        ss_id = '1wBVKv14zcMLZawsT20JBt6FDxpzLDdppAJoFPgJ2La4'
        project = 'test'
        url = 'https://yandex.md/maps/org/avtomir_mazda/86615003593/reviews/?ll=37.679170%2C55.853506&z=16'
        links = []
        rating_max = 5
        ranking = "by_time"   # самые свежие отзывы
        max_pages = 1         # пагинация не нужна — запуск будет частым

        list_datas = await blocks_ya_reviews_api(service, url, ss_id, project, links, rating_max, ranking, max_pages)
        pprint(list_datas)

    asyncio.run(main())