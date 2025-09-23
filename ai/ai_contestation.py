import sys
sys.excepthook = sys.__excepthook__


import asyncio
import os

import re
import time
from datetime import datetime

import selenium.common.exceptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


import pandas as pd

from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

from models.mdl_tables import ForumRules

from portals.portal_ya import main_ya_maps
from portals.portal_2gis import blocks_2gis_bs4
from portals.portal_zoon import zoon_blocks

from utils.ai_module import get_answer_ai
from utils.central_module import wait_for_portal, get_hpo

from utils.constants import TABLES_LIST
from utils.db_loader import read_data_from_db_filter

from utils.gs_editor import get_service, write_log_sheet, get_table_scope, append_data_to_sheet_cell, \
    append_data_to_sheet_cells, append_data_to_sheet_scopes, read_table_id, append_data_to_sheet_scope

from portals.portal_otzovik import get_top_link
from portals.portal_ya import get_json, get_id_org
from portals.portal_tripadvisor import blocks_tripadvisor_sel
from portals.pravda_sotrudnikov import blocks_pravda
from portals.otzovru import blocks_otzovru


from utils.user_agent import get_soup, get_selenium_proxy, get_soup_tor, get_soup_bs4, clean_html

from utils.constants import months

import textwrap

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

max_sec = int(os.environ.get("MAX_SEC"))

username = os.environ.get("HOST_USERNAME")
password = os.environ.get("HOST_PASSWORD")
auth = HTTPBasicAuth(username, password)


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

#market = 'Vkusvill'
worktable_id = '1FLCSWjY9vWv2Lf1hVB4BORfXK3B1tCvx85su2ZHAKyY'
ss_id = '1FLCSWjY9vWv2Lf1hVB4BORfXK3B1tCvx85su2ZHAKyY'
#worksheet_name = TABLES_LIST[market][1]
#worksheet_name_dreamjob = 'reviews_dreamjob'
#print(worktable_id, worksheet_name)

headless, proxy_on, only_text = asyncio.run(get_hpo())

async def empty_data():
    datas = {
        "Дата": [],
        "Текст": [],
        "Бренд": [],
        "Источник": [],
        "Url": [],
        "Автор": [],
        "Оценка": [],
        "Общий Url": [],
        "Кол-во отзывов": [],
        "Оценка компании до удаления": [],
        "Вероятность удаления": [],
        "Текст для поддержки": []
    }
    return datas

async def get_links(service, ss_id, project):
    try:
        df_links = await read_table_id(service, ss_id, project)
        links = df_links['Url'].tolist()
    except:
        links = []

    return links

async def move_mouse():
    import pyautogui

    print("Скрипт запущен. Мышь будет двигаться каждые 5 минут, чтобы предотвратить засыпание экрана.")
    print("Чтобы остановить, нажмите CTRL+C.")

    try:
        while True:
            # Получаем текущие координаты мыши в отдельном потоке
            x, y = await asyncio.to_thread(pyautogui.position)

            # Перемещаем мышь на 1 пиксель вправо в отдельном потоке
            await asyncio.to_thread(pyautogui.moveTo, x + 10, y, duration=0.25)
            print(f"Мышь перемещена на 1 пиксель вправо. Новые координаты: ({x}, {y})")

            # Асинхронно ждем 30 секунд. Это не блокирует другие задачи.
            await asyncio.sleep(30)
            # Получаем текущие координаты мыши в отдельном потоке
            x, y = await asyncio.to_thread(pyautogui.position)

            # Перемещаем мышь обратно в отдельном потоке
            await asyncio.to_thread(pyautogui.moveTo, x - 10 , y, duration=0.25)
            print(f"Мышь перемещена на 1 пиксель влево. Новые координаты: ({x}, {y})")

            # Асинхронно ждем 30 секунд перед следующим циклом
            await asyncio.sleep(30)

    except KeyboardInterrupt:
        print("\nСкрипт остановлен пользователем.")
        # sys.exit() не рекомендуется в асинхронном коде. Лучше обработать
        # исключение в main() или вернуть управление.
        pass # Просто выходим из цикла

async def review_analysis(worktable_id, tab_name):
    '''Функция для анализа отзыва'''

    service = await get_service()

    # ws_name = worksheet_name_dreamjob

    try:
        df = await get_table_scope(service, worktable_id, tab_name)
        print(df)

    except Exception as Ex:
        print(f"Error: {Ex}")
        return
    # add_column = 'Текст для поддержки'
    # df = df[df[add_column]=='']

    columns = ['Вероятность удаления', 'Текст для поддержки']
    # for column in columns:
    #     df[column] = ''

    for idx, row in df.iterrows():
        probably_delete = row[columns[0]]
        text_support = row[columns[1]]

        if pd.notnull(probably_delete) and pd.notnull(text_support):
            continue

        print(f'IDX = {idx}')

        brand = row['Бренд']
        link = row['Url']
        comment = row['Текст']
        source = row['Источник']
        #rating = float(row['Оценка'])
        #
        # if rating > rating_before: #если рейтинг выше нужного, пропускает отзыв
        #     continue

        if 'yandex.ru/maps' in source:
            project = 'yandex_maps'

        else:
            project = source.split('.')[0]

        print("project: ", project)

        status, rules_db = await read_data_from_db_filter(ForumRules, forum_name=project)
        if status:
            if len(rules_db) > 0:
                rule = rules_db[0].forum_rule

            else:
                continue

        else:
            continue

        prompt = text.format(source=source, comment=comment, rule=rule)
        result = await get_answer_ai(auth, prompt)
        print(result)

        try:
            result = eval(result)
            if '49' in result[0]:
                pass
            else:
                result[1] = (f"Здравствуйте, "
                             f"Я представляю интересы компании '{brand}' и хочу обратиться с просьбой удалить отзыв по ссылке {link}. "
                             f"Отзыв содержит нарушение:\n") + result[1]

            await append_data_to_sheet_cells(service, worktable_id, brand, columns, idx + 2, result)

        except SyntaxError as SE:
            print(f'ERROR: {SE}')

async def extract_link_from_line(url):
    # Шаблон для поиска ссылки от https: до .html
    pattern = r"https:.*?\.html"
    # Поиск ссылки в строке
    match = re.search(pattern, url)
    if match:
        return match.group(0)
    return None

async def review_analysis_old(service, brand):
    """
    Функция для анализа отзыва
    Args:
        service:
        brand:
    Returns:
    """
    df = await get_table_scope(service, worktable_id, brand)
    add_column = 'Текст для поддержки'
    df = df[df[add_column].isnull()]
    print(df)

    for idx, row in df.iterrows():
        print(idx)
        link = row['Url']
        comment = row['Текст']
        source = row['Источник']

        if 'yandex.ru/maps' in source:
            project = 'yandex_maps'

        else:
            project = source.split('.')[0]

        status, rules_db = await read_data_from_db_filter(ForumRules, forum_name=project)
        print(status)

        if status:
            if len(rules_db) > 0:
                print(1)
                rule = rules_db[0].forum_rule

            else:
                print(2)
                continue

        else:
            continue

        prompt = text.format(source=source, comment=comment, rule=rule)
        result = await get_answer_ai(auth, prompt)
        print(result)

        try:
            result = eval(result)
            result[1] = f"Здравствуйте, Я представляю интересы компании {brand} и хочу обратиться с просьбой удалить отзыв {link}. Отзыв содержит нарушение:\n" + result[1]

            columns = ['Вероятность удаления', 'Текст для поддержки']
            await append_data_to_sheet_cells(service, worktable_id, brand, columns, idx + 2, result)

        except SyntaxError as SE:
            print(f'ERROR: {SE}')

async def main_vkusvill():
    service = await get_service()
    await cheak_vkusvill(service)

    data = {'service_name': market, 'date': time.ctime()}
    await write_log_sheet(service, '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8', 'logs', data)

async def grade_analysis(worktable_id, worksheet_name):
    service = await get_service()

    df = await get_table_scope(service, worktable_id, worksheet_name)
    not_null = 'Текст'
    is_null = 'Общий Url'
    df = df[(df[not_null].notnull() & df[is_null].isnull())]

    columns = ['Общий Url', 'Ссылка Url']

    print(df)
    for idx, row in df.iterrows():
        portal = row['Источник']
        link = row['Url']
        print(link)

        if portal == 'otzovik.com':
            feeback_link = await extract_link_from_line(link)

            await wait_for_portal()
            status, top_link = await get_top_link(link) #Получаем топовую ссылку
            if not status:
                result = ['Ошибка, проверить страницу на актульность.', feeback_link]
                await append_data_to_sheet_cells(service, worktable_id, worksheet_name, columns, idx + 2, result)
                await asyncio.sleep(5)
                continue

            print("top_link",top_link)

            soup = await get_soup(top_link)
            if not soup:
                await asyncio.sleep(5)
                continue

            error_page = soup.find('h1')
            for er in error_page:
                if 'Ошибка' in er.text:

                    result = ['Ошибка, проверить страницу на актульность.', feeback_link]
                    await append_data_to_sheet_cells(service, worktable_id, worksheet_name, columns, idx + 2, result)
                    await asyncio.sleep(5)
                    continue

            overall_grade = soup.find('div', class_='rating-score-2 big').text.strip()
            number_grades = soup.find('span', class_='votes').text.strip()

            columns = ['Общий Url', 'Ссылка Url', 'Кол-во отзывов', 'Оценка компании до удаления']
            result = [top_link, feeback_link, number_grades, overall_grade]
            await append_data_to_sheet_cells(service, worktable_id, worksheet_name, columns, idx + 2, result)

            await asyncio.sleep(5)

        elif portal == 'nerab.ru':
            pass

async def total_grade_analysis(service, tn_name):
    '''
    Функция для подсчета рейтинга после удаления отзыва
    '''

    df = await get_table_scope(service, worktable_id, tn_name)

    data_rows = []

    for idx, row in df.iterrows():
        company_link = row['Общий Url']
        feedback_counts = row['Кол-во отзывов']

        if pd.isna(feedback_counts):
            # print('Next...')
            continue

        #df = df[(df[add_column] == '') & (df[add_column_2].str.contains(r'([5-9][0-9]|[1-9][0-9]{2,})'))]
        df_mini = df[(df['Общий Url'] == company_link) & (df['Вероятность удаления'].str.contains(r'([5-9][0-9]|[1-9][0-9]{2,})'))]

        df_mini = df_mini.drop_duplicates(subset=["Ссылка Url"]) #Удаляем дублика ссылок!!!!!!!!!!!!!!!!!!!!!!
        df_mini["Оценка"] = pd.to_numeric(df_mini["Оценка"], errors='coerce')  # Преобразуем в числа

        counts_feedback = float(df_mini['Кол-во отзывов'].iloc[-1])
        company_rating = float(df_mini['Оценка компании до удаления'].iloc[-1])

        total_sum = counts_feedback * company_rating
        total_negative_sum = df_mini["Оценка"].sum()
        total_negative_count = df_mini["Оценка"].count()

        finish_sum = total_sum - total_negative_sum
        finish_counts = counts_feedback - total_negative_count
        finish_rating = round(finish_sum / finish_counts, 1)

        for idx_mini, row_mini in df_mini.iterrows():
            rating = row_mini['Оценка компании после удаления']

            if pd.notnull(rating):
                continue

            if idx_mini not in data_rows:
                await append_data_to_sheet_cell(service, worktable_id, tn_name,'Оценка компании после удаления', idx_mini + 2, finish_rating)
                print(f'{idx_mini} Add info...')
                data_rows.append(idx_mini)

async def pars_dreamjob(service, top_url, proxy_on):
    """Функция для получения негативных отзывовов и записьм их в таблицу"""
    unix_time = str(int(time.time() * 1000))

    #https://dreamjob.ru/employers/56859?employerId=56859&erfrp%5BlastParam%5D=&erfrp%5Bfrom_vacancy%5D=&sort=-total_rating&page=1&_=1730535359347
    #https://dreamjob.ru/employers/56859?employerId=56859&erfrp%5BlastParam%5D=ratings&erfrp%5Bfrom_vacancy%5D=&sort=-total_rating&erfrp%5Bratings%5D%5B%5D=1&page=1&_=1730535359348

    soup = await get_soup(top_url, proxy=proxy_on)
    if not soup:
        return

    brand = soup.find('div', {'class': 'company__name line-clamp-2', 'data-js': 'companyName'}).text.strip()
    print(brand)

    df = await get_table_scope(service, worktable_id, brand)
    df_urls = df['Url'].to_list()

    total_rating = soup.find('div', {"class": 'dashboard__grade-total'}).text
    print(total_rating)
    total_rating = float(total_rating.replace(',', '.'))
    print(total_rating)

    try:
        total_reviews_content = soup.find('span', {"class": 'tabs__count'}).text
        print(total_reviews_content)
        total_reviews = int(total_reviews_content.replace(' ', ''))
        print(total_reviews)

    except:
        total_reviews_content = soup.find('div', {"class": 'dashboard__grade-reviews'}).text
        total_reviews_split = total_reviews_content.split(' ')[0]
        print(total_reviews_split)
        total_reviews = int(total_reviews_split.replace(' ', ''))
        print(total_reviews)

    employerId = top_url.split('/')[-1]

    # pages = ['1',
    #          '2.2',
    #          '3.3666666666666667',
    #          '4.533333333333333',
    #          '5.7',
    #          '6.866666666666666']

    #for page in pages:
    page_int = 30
    while True:
        page_int += 1
        page = str(page_int)
        print(f'\nPage: {page}')

        url = (f'{top_url}?'
               f'employerId={employerId}&'
               f'sort=total_rating&'
               f'erfrp%5Bratings%5D%5B%5D=2&'
               f'erfrp%5Bratings%5D%5B%5D=1&'
               f'page={page}&'
               f'_={unix_time}')

        soup = await get_soup(url, proxy=proxy_on)
        if not soup:
            continue

        blocks = soup.find_all('div', {"class": 'review', 'data-partly': 'short'})
        print('Len:', len(blocks))
        if len(blocks) == 0:
            return None

        datas = {'Дата': [],
                 'Заголовок': [],
                 'Текст': [],
                 'Бренд': [],
                 'Источник': [],
                 'Url': [],
                 'Автор': [],
                 'Оценка': [],
                 'Общий Url': [],
                 'Ссылка Url': [],
                 'Кол-во отзывов': [],
                 'Оценка компании до удаления': []
                 }

        for block in blocks:
            #print('\n*******************************************')
            try:
                date = block.find_next('div', {'class': 'review__header-date'}).text
            except:
                date_content = block.find_all('div', {'class': 'tags__item'})[1].text
                data_split = date_content.split(',')[-1]
                date = data_split.strip()

            title = block.find_next('h2', {'class': 'review__header-title'}).text.strip()
            #print(title)

            title_div_plus = block.find('div', class_='review__title review__gap')
            plus_title = title_div_plus.text
            # print(plus_title)

            # Находим следующий div
            next_div = title_div_plus.find_next('div', class_='review__title')

            # Получаем весь текст между двумя div
            full_text = ''
            for sibling in title_div_plus.next_siblings:
                if sibling == next_div:
                    break

                if isinstance(sibling, str):
                    full_text += sibling
                elif sibling.name == 'br':
                    full_text += '\n'

            # Очищаем текст от лишних пробелов и переносов строк
            plus = ' '.join(full_text.split())
            # print(plus)

            title_div_minus = block.select_one('div.review__title:not(.review__gap)')
            # print(title_div_minus)
            minus_title = title_div_minus.text
            # print(minus_title)

            if title_div_minus:
                minus = title_div_minus.find_next_sibling(text=True).strip()
                # print(minus)

            feedback = f"""{plus_title}:
{plus}
{minus_title}:
{minus}
"""

            feedback = textwrap.dedent(feedback)
            #print(feedback)

            portal = 'dreamjob.ru'

            url_answer = block.find('a', {'class': 'bt bt--32 bt--primary-link icon-copy'}).get('href')
            if not url_answer:
                url_answer = block.find('a', role='button', tabindex='0').get('href')

            if not url_answer:
                url_answer = block.find('a', tabindex='0').get('href')
            #print(url_answer)

            if url_answer in df_urls:
                continue

            author = block.find('h2', {'class': 'review__header-title'}).text.strip()
            #print(author)

            #rating = block.find('div', {'class': 'review__header-title'}).text.strip()
            rating = soup.find(lambda tag: tag.name == "div" and "class" in tag.attrs and "data-partly-switch" in tag.attrs).text.strip()
            rating = float(rating.replace(',', '.'))
            #print(rating)

            if rating >= 3:
                return

            #top_url = 'https://dreamjob.ru/employers/56859'

            #print(date)

            datas['Дата'].append(date)
            datas['Заголовок'].append(title)
            datas['Текст'].append(feedback)
            datas['Бренд'].append(brand)
            datas['Источник'].append(portal)
            datas['Url'].append(url_answer)
            datas['Автор'].append(author)
            datas['Оценка'].append(rating)
            datas['Общий Url'].append(top_url)
            datas['Ссылка Url'].append(url_answer)
            datas['Кол-во отзывов'].append(total_reviews)
            datas['Оценка компании до удаления'].append(total_rating)

        await append_data_to_sheet_scopes(service, worktable_id, brand, datas)
        print('White datas - OK!')
        await asyncio.sleep(5)

async def pars_2gis(service, url, ss_id, project, links, rating_max):
    source = '2gis.ru'
    blocks, branch_rating, branch_reviews_count = await blocks_2gis_bs4(url)

    for block in blocks:
        url_answer = block['id']
        if url_answer in links:
            print('Такой комментарий уже есть в списке')
            continue

        rating = block['rating']

        if rating > rating_max:
            continue

        date_content = block['date_created']
        date = datetime.strptime(date_content, "%Y-%m-%dT%H:%M:%S.%f%z")
        formatted_date = date.strftime("%d.%m.%Y")

        feedback = block['text']
        author = block['user']['name']

        datas = await empty_data()

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

        await append_data_to_sheet_scopes(service, ss_id, project, datas)

async def pars_zoon(service, driver, url, ss_id, project, links, rating_max):
    driver.get(url)
    await asyncio.sleep(5)

    source = 'zoon.ru'

    try:
        number_reviewss = driver.find_elements(By.CSS_SELECTOR, 'span[class="service-block-nav-item-count z-text--13"]')
        print("Leb_NR", len(number_reviewss))
        number_reviews = int(number_reviewss[1].text)

    except:
        number_reviewss = driver.find_element(By.CSS_SELECTOR, 'div[data-uitest="count_reviews_in_total"]').text
        print("number_reviewss:", number_reviewss)
        number_reviews = int(number_reviewss.split(' ')[0])
        print("number_reviewss:", number_reviews)

    if number_reviews == 0:
        return

    rating_befores = driver.find_element(By.CSS_SELECTOR, 'div[data-target="rating-total"]').text
    rating_before = float(rating_befores.replace(',', '.'))

    print(number_reviews, rating_before)

    content = await zoon_blocks(driver, url, rating_max)
    df = pd.DataFrame(content)

    datas = await empty_data()

    for k, row in df.iterrows():
        url_answer = row['Url']
        if url_answer in links:
            print('Такой комментарий уже есть в списке')
            continue

        rating = row['Оценка']
        if rating > rating_max:
            continue

        formatted_date = row['Дата']
        feedback = row['Текст']
        author = row['Автор']

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

async def pars_otzyvru(service, driver, url, ss_id, project, links, rating_max):
    source = 'otzyvru.com'

    page = 1
    while True:
        link = f"https://www.otzyvru.com/servis-poiska-vrachey-docdoc?sort=rating_asc&page={page}"
        blocks = await blocks_otzovru(driver, link)

        if len(blocks) == 0:
            return

        btn_blue = driver.find_element(By.CSS_SELECTOR, 'a[class="btn blue"]')
        print(btn_blue == True)

        for block in blocks:
            url_answer = block.find_element(By.CSS_SELECTOR, 'h2').find_element(By.CSS_SELECTOR, 'a[href]').get_attribute('href')
            print(url_answer)

            if url_answer in links:
                continue

            rating_content = block.find_element(By.CSS_SELECTOR, 'span[style]').get_attribute('style')
            print(rating_content)
            rating_json = {'width:13px;': 1,
                           'width: 13px;': 1,
                            'width:26px;': 2,
                            'width:39px;': 3,
                            'width:52px;': 4,
                            'width:65px;': 5}

            rating = rating_json[rating_content]
            print(rating)

            if rating > rating_max:
                return

            author = block.find_element(By.CSS_SELECTOR, 'span[class="reviewer"][itemprop="name"]').text
            print(author)

            date_content = block.find_element(By.CSS_SELECTOR, 'span[class="value-title"][title]').get_attribute('title')
            date = datetime.strptime(date_content, "%Y-%m-%d")
            formatted_date = date.strftime("%d.%m.%Y")
            print(formatted_date)

            comment_description = block.find_element(By.CSS_SELECTOR, 'span[class="comment description"]')

            try:
                text = comment_description.find_element(By.CSS_SELECTOR, 'span[class="review-full-text none"]').text

            except:

                text = comment_description.find_element(By.CSS_SELECTOR, 'span[class="review-snippet"]').text

            advantages = comment_description.find_element(By.CSS_SELECTOR, 'span[class="advantages"]').text
            disadvantages = comment_description.find_element(By.CSS_SELECTOR, 'span[class="disadvantages"]').text


            feedback = f"{text}\n"


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







async def main_grade():
    headless, proxy_on, only_text = await get_hpo()
    service = await get_service()

    top_urls = ['https://dreamjob.ru/employers/56859',
               'https://dreamjob.ru/employers/25946']


    top_urls = ['https://dreamjob.ru/employers/25946']

    # for top_url in top_urls:
    #     await pars_dreamjob(service, top_url, proxy_on)

    await cheak_dreamjob(service, 'МТС')

    #asyncio.run(main_vkusvill())
    #await cheak_dreamjob(service)

    #asyncio.run(grade_analysis())
    #await total_grade_analysis(service, 'reviews')

async def get_feedback_irec_sel(driver2, url):

    while True:
        try:
            driver2.get(url)
            await asyncio.sleep(5)

            feedback = driver2.find_element(By.CSS_SELECTOR, 'a[class="review-summary active"]').text
            break

        except Exception as Ex:
            print(f'- Error Ex: {Ex}')
            await asyncio.sleep(5)

    description_content = driver2.find_element(By.CSS_SELECTOR, 'div[class="description hasinlineimage"]').text
    description = await clean_html(description_content)
    #input(description)

    # ps = driver2.find_elements(By.CSS_SELECTOR, 'p')
    # for p in ps:
    feedback += f"\n{description}"
    return textwrap.fill(feedback, width=200)

async def get_feedback_irec(url):

    while True:
        try:
            #soup = await get_soup_tor(url)
            soup = await get_soup(url, proxy=proxy_on)
            feedback = soup.find("a", {"class": "review-summary active"}).text
            break

        except Exception as Ex:
            print(f'- Error Ex: {Ex}')
            await asyncio.sleep(5)

    ps = soup.find_all('p')
    for p in ps:
        feedback += p.text
    return textwrap.fill(feedback, width=200)

async def get_feedback_otz1(driver, url):
    print(f'- New page: {url}')
    main_tab = driver.current_window_handle
    print(f'- Main tab = {main_tab}')
    # Открываем новую вкладку с помощью JavaScript
    driver.execute_script("window.open('');")

    print('- Len tabs: ', len(driver.window_handles))
    print('- Switch to new tab')
    # Переключаемся на новую вкладку (индекс 1, так как вкладки нумеруются с 0)
    #driver.switch_to.window(driver.window_handles[1])
    await asyncio.sleep(5)

    print(f'- Driver get: {driver.current_window_handle}')
    driver.get(url)
    await asyncio.sleep(5)

    #
    #
    # print("driver.window_handles: ", driver.window_handles)
    # for idx, tab in enumerate(driver.window_handles):
    #     print("-- driver tab", idx, tab)
    #     print("-- driver current", driver.current_window_handle)
    #
    #     if main_tab != driver.current_window_handle:
    #         break
    #
    #     else:
    #         print('- Переключаем на другую вкладку')
    #         driver.switch_to.window(driver.window_handles[idx + 1])
    #         await asyncio.sleep(1)

    print(driver.current_window_handle)
    print("---- 1")
    print(driver.current_window_handle)

    topic = ''
    topics = driver.find_elements(By.CSS_SELECTOR, 'h1')
    for i, tpc in enumerate(topics):
        try:
            if i == 1:
                topic = tpc.text

        except:
            break

    print('---- 2')

    plus = driver.find_element(By.CSS_SELECTOR, 'div[class="review-plus"]').text
    minus = driver.find_element(By.CSS_SELECTOR, 'div[class="review-minus"]').text
    try:
        text = driver.find_element(By.CSS_SELECTOR, 'div[class="review-body description"]').text

    except selenium.common.exceptions.NoSuchElementException as NSEE:
        text = 'NO DATA'

    finally:
        print('-- Close Tab')
        await asyncio.sleep(5)
        try:
            driver.close()
            driver.switch_to.window(driver.window_handles[idx])  # Вернуться на первую вкладку

        except Exception as e:
            print(f"- Ошибка при закрытии вкладки: {e}")

    print('-- return Feedback datas')
    return topic + "\n" + plus + "\n" + minus + "\n" + text

async def get_feedback_otz(driver, url):
    #driver = await get_selenium_proxy(url, headless=False, proxy=False)
    driver.get(url)

    n = 0
    while n < 10:
        try:
            plus = driver.find_element(By.CSS_SELECTOR, 'div[class="review-plus"]').text
            break

        except:
            n += 1
            print(n, 'Plus')
            await asyncio.sleep(2)

            if n == 5:
                driver.refresh()

    # print("driver.window_handles: ", driver.window_handles)
    # for idx, tab in enumerate(driver.window_handles):
    #     print("-- driver tab", idx, tab)
    #     print("-- driver current", driver.current_window_handle)
    #
    #     if main_tab != driver.current_window_handle:
    #         break
    #
    #     else:
    #         print('- Переключаем на другую вкладку')
    #         driver.switch_to.window(driver.window_handles[idx + 1])
    #         await asyncio.sleep(1)

    #print(driver.current_window_handle)
    print("---- 1")
    #print(driver.current_window_handle)

    topic = ''
    topics = driver.find_elements(By.CSS_SELECTOR, 'h1')
    for i, tpc in enumerate(topics):
        try:
            if i == 1:
                topic = tpc.text

        except:
            break

    print('---- 2')

    # try:
    #     plus = driver.find_element(By.CSS_SELECTOR, 'div[class="review-plus"]').text
    # except:
    #     return

    n = 0
    while n < 10:
        try:
            minus = driver.find_element(By.CSS_SELECTOR, 'div[class="review-minus"]').text
            break

        except:
            n += 1
            print(n, 'Minus')
            await asyncio.sleep(2)

            if n == 5:
                driver.refresh()


    try:
        text = driver.find_element(By.CSS_SELECTOR, 'div[class="review-body description"]').text

    except selenium.common.exceptions.NoSuchElementException as NSEE:
        text = 'NO DATA'

    finally:
        print('-- Close Tab')
        await asyncio.sleep(1)
        try:
            #driver.quit()
            #driver.switch_to.window(driver.window_handles[idx])  # Вернуться на первую вкладку
            pass

        except Exception as e:
            print(f"- Ошибка при закрытии вкладки: {e}")

    print('-- return Feedback datas')
    return topic + "\n" + plus + "\n" + minus + "\n" + text

async def pars_otzovik(service, driver, url, driver2, ss_id, project, links, ratio, start_page):
    import locale
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')

    driver.get(url)
    await asyncio.sleep(10)

    pages = 1000
    source = "otzovik.com"

    rating_box = driver.find_element(By.CSS_SELECTOR, 'div[class="rating-score-wrap"]')
    rating_box = rating_box.text.split('\n')[0]
    rating_before = float(rating_box)
    print(rating_before)

    number_box = driver.find_element(By.CSS_SELECTOR, 'span[class="reviews-counter"]')
    print(number_box.text)
    number_box2 = number_box.text.split(':')[1]
    print(number_box2)
    number_reviews = int(number_box2)
    print(number_reviews)
    #input()

    #rating_before = 2.9
    #number_reviews = 41

    list_temp = []

    async def blocks_otz(block, service):
        try:
            date_string = block.find_element(By.CSS_SELECTOR, 'div[class="review-postdate"]').text
        except:
            await asyncio.sleep(1)
            date_string = block.find_element(By.CSS_SELECTOR, 'div[itemprop="datePublished"]').text

        # Преобразуем строку в объект datetime
        date_object = datetime.strptime(date_string, '%d %b %Y')
        # Форматируем объект datetime в нужную строку
        formatted_date = date_object.strftime('%d.%m.%Y')

        author = block.find_element(By.CSS_SELECTOR, 'span[itemprop="name"]').text
        rating = int(block.find_element(By.CSS_SELECTOR, 'div[class="rating-score tooltip-right"]').text)

        #print("- Rating:", rating)
        if rating > ratio:
            print()
            print(f'- Next, Rating {rating} >= 3')
            return

        url_answer = block.find_element(By.CSS_SELECTOR, 'meta[itemprop="discussionUrl"]').get_attribute("content")
        if url_answer in links:
            #print(url_answer)
            #print('- Url in links')
            return

        if url_answer in list_temp:
            return

        else:
            list_temp.append(url_answer)

        feedback = await get_feedback_otz(driver2, url_answer)

        datas = await empty_data()

        datas['Дата'].append(formatted_date)
        datas['Текст'].append(feedback)
        datas["Бренд"].append(project)
        datas["Источник"].append(source)

        datas['Url'].append(url_answer)
        datas['Автор'].append(author)
        datas['Оценка'].append(rating)

        datas["Общий Url"].append(url)
        datas["Кол-во отзывов"].append(number_reviews)
        datas["Оценка компании до удаления"].append(rating_before)

        await append_data_to_sheet_scopes(service, ss_id, project, datas)
        print(url_answer)
        print('-- White datas - OK!\n')
        #input('Next...')

    for rt in range(1, ratio + 1):
        for page in range(start_page, pages + 1):
            url_com = f"{url}/{page}/?ratio={str(rt)}"
            driver.get(url_com)
            print(f'\n\nStart: {url_com}')
            print(f"Page {page}")

            n = 0
            while n < 10:
                try:
                    blocks = driver.find_elements(By.CSS_SELECTOR, 'div[itemprop="review"]')
                    len_b = len(blocks)

                    if len_b == 0:
                        n += 1
                        print(n)
                        await asyncio.sleep(1)

                    else:
                        print(f'Len b = {len_b}')
                        break

                except:
                    n += 1
                    print(n)
                    await asyncio.sleep(1)

            for block in blocks:
                await blocks_otz(block, service)
                await asyncio.sleep(1)

            try:
                next_page = driver.find_element(By.CSS_SELECTOR, 'a[class][title="Следующая страница"]').text
                await asyncio.sleep(1)
            except:
                break

        #url_o = url + str(page) + "/?ratio=N"

async def pars_irec(service, driver, driver2, url, ss_id, project, links, rating_max):
    driver.get(url)
    await asyncio.sleep(5)

    source = "irecommend.ru"

    n = 0
    while n < 3:
        try:
            selectors = ['li[class="pager-last last"]', 'li[class="pager-last"]']
            #Кол-во страницы для парсинга на портале
            for selector in selectors:
                try:
                    pages = int(driver.find_element(By.CSS_SELECTOR, selector).text)
                    print("Pages: ", pages)
                    await asyncio.sleep(1)

                except:
                    continue

            if pages:
                break

        except:
            n += 1
            print(f'Error: {n}')
            await asyncio.sleep(2)

    number_reviews = int(driver.find_element(By.CSS_SELECTOR, 'span[itemprop="reviewCount"]').text)
    print(number_reviews)

    rating_before = float(driver.find_element(By.CSS_SELECTOR, 'span[itemprop="ratingValue"]').text)
    print(rating_before)

    temp_lists = []

    for page in range(0, pages + 1): #начинается со страницы 0
        url_o = url + f"?page={page}"
        print(f'\n\nStart: {url_o}')
        driver.get(url_o)
        await asyncio.sleep(7)

        blocks = driver.find_elements(By.CSS_SELECTOR, 'div[data-type="1"]')
        # print('- 2')
        len_b = len(blocks)

        for block in blocks:
            rating_content = block.find_elements(By.CSS_SELECTOR, 'div[class="on"]')
            rating = len(rating_content)

            if rating > rating_max:
                continue

            url_answer = block.find_element(By.CSS_SELECTOR, 'a[class="reviewTextSnippet"]').get_attribute("href")
            if url_answer in links:
                continue

            if url_answer in temp_lists:
                continue
            else:
                temp_lists.append(url_answer)

            print("- url_feedback:", url_answer)
            feedback = await get_feedback_irec_sel(driver2, url_answer)

            formatted_date = block.find_element(By.CSS_SELECTOR, 'div[class="created"]').text
            author = block.find_element(By.CSS_SELECTOR, 'div[class="authorName"]').text

            datas = await empty_data()

            datas['Дата'].append(formatted_date)
            datas['Текст'].append(feedback)
            datas["Бренд"].append(project)
            datas["Источник"].append(source)

            datas['Url'].append(url_answer)
            datas['Автор'].append(author)
            datas['Оценка'].append(rating)

            datas["Общий Url"].append(url)
            datas["Кол-во отзывов"].append(number_reviews)
            datas["Оценка компании до удаления"].append(rating_before)

            await append_data_to_sheet_scopes(service, ss_id, project, datas)
            await asyncio.sleep(5)
            print(f'--- append {author}')

async def pars_ya_maps(service, driver, url, ss_id, project, links, rating_max):
    org_id = await get_id_org(url)
    source = "yandex.ru/maps"

    url = f'https://yandex.kz/maps/org/{org_id}/reviews'
    print(url)
    driver.get(url)
    await asyncio.sleep(5)

    n = 0
    while True:
        try:
            reviews_element = driver.find_element(By.CSS_SELECTOR, 'h2[class="card-section-header__title _wide"]')
            reviews_text = reviews_element.text
            number_reviews = int(reviews_text.split(" ")[0])
            print(f"--- 1 {number_reviews}")
            break

        except:
            try:
                reviews_element = driver.find_element(By.CSS_SELECTOR,
                                                      'h2[class="card-section-header__title"]')
                reviews_text = reviews_element.text
                number_reviews = int(reviews_text.split(" ")[0])
                print(f"--- 2 {number_reviews}")
                break

            except Exception as Ex:
                print(f'3 Error: {Ex}')
                await asyncio.sleep(2)

                n += 1

                if n > 10:
                    return

    try:
        rating_befores = driver.find_elements(By.CSS_SELECTOR,
                                             'span.business-summary-rating-badge-view__rating-text')

        rating_before = float(rating_befores[0].text + '.' + rating_befores[2].text)

    except:
        rating_before = None

    #number_reviews = 200

    while True:
        blocks = driver.find_elements(By.CSS_SELECTOR, 'div[class="business-reviews-card-view__review"]')
        len_b = len(blocks)
        print("Скрол вниз:", len_b)
        await asyncio.sleep(3)

        if len_b == number_reviews:
            break

    for k, block in enumerate(blocks):
        print(k)
        formatted_date = block.find_element(By.CSS_SELECTOR, 'span[class="business-review-view__date"]').text

        try:
            spoiler = block.find_element(By.CSS_SELECTOR, 'span[class="spoiler-view__button"]')
            spoiler.click()
            print('-> Click spoiler')
            await asyncio.sleep(2)

        except Exception as Ex:
            feedback = block.find_element(By.CSS_SELECTOR, 'span[class=" spoiler-view__text-container"]').text
            print(f'- Нет спойлера\n{feedback}')

        feedback = block.find_element(By.CSS_SELECTOR, 'span[class=" spoiler-view__text-container"]').text

        # if feedback in texts:
        #     continue

        try:
            url_author = block.find_element(By.CSS_SELECTOR,
                                            'a[class="business-review-view__user-icon"]').get_attribute("href")
            url_author_split = url_author.split('/')[-1]
            url_answer = f'https://yandex.md/maps/org/{org_id}/reviews?reviews%5BpublicId%5D={url_author_split}&utm_source=review'

            if url_answer in links:
                continue
        except:
            url_answer = ''

        try:
            author = block.find_element(By.CSS_SELECTOR, 'span[itemprop="name"]').text
        except:
            author = block.find_element(By.CSS_SELECTOR, 'span[dir="auto"]').text

        star_full = block.find_elements(By.CSS_SELECTOR,
                                        'span[class="inline-image _loaded icon business-rating-badge-view__star _full"]')
        rating = len(star_full)

        if rating > rating_max:
            continue

        datas = await  empty_data()

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

async def pars_tripadvisor(service, driver, url, ss_id, project, links, rating_max):
    source = 'tripadvisor.ru'
    number_reviews = 1839
    rating_before = 3.9

    driver.get(url)

    for i in range(1, 55):
        print(f"----------------page-{i}----------------------")

        # offset = f'r{str((i - 1) * 10)}'
        # url = f'https://www.tripadvisor.ru/Attraction_Review-g298484-d8514577-Reviews-o{offset}-Moskvarium-Moscow_Central_Russia.html'

        blocks = await blocks_tripadvisor_sel(driver, url)

        print(blocks)
        print(len(blocks))
        #await asyncio.sleep(10)

        datas = await  empty_data()

        for block in blocks:
            url_answer = block['url_answer']
            if url_answer in links:
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

            #await asyncio.sleep(1)

        await append_data_to_sheet_scopes(service, ss_id, project, datas)
        await asyncio.sleep(3)

async def pars_pravda(service, url, ss_id, project, links):
    source = 'pravda-sotrudnikov.ru'
    rating = None

    soup = await get_soup(url, proxy=False)

    number_reviews = soup.find('span', {'class': 'company-reviews-title-quantity'}).text
    print(number_reviews)

    rating_before = soup.find('div', {'class': 'company-info-contacts-row'}).find('span', {'class': "rating-autostars"}).get('data-rating')
    print(rating_before)

    last_page = 1
    li = soup.find_all('li')
    for l in li:
        txt = l.text
        if txt.isdigit():
            last_page = int(txt)

    print(f'Last page: {last_page}')

    for i in range(last_page):
        url_page = url + f'?page={i+1}'
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
                #author = "\n".join(line.strip() for line in author.splitlines() if line.strip())
                author = " ".join(author.split())

                text = block.find('div', {'class': 'row'}).text
                feedback = "\n".join(line.strip() for line in text.splitlines() if line.strip())

                datas = await  empty_data()

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





async def main_stroyenergokom():
    service = await get_service()
    driver = await get_selenium_proxy(headless=False, proxy=False)
    project = 'СтройЭнергоКом'

    urls = ['https://yandex.kz/maps/org/stroyenergokom/200448132769/reviews/?ll=37.625540%2C55.706822&z=16',
            'https://yandex.kz/maps/org/stroyenergokom/157241800880/reviews/?ll=57.075250%2C56.146695&z=3',
          ]

    for url in urls:
        driver.get(url)

        await asyncio.sleep(5)

        reviews_element = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'h2[class="card-section-header__title _wide"]'))
        )
        reviews_text= reviews_element.text
        number_reviews = int(reviews_text.split(" ")[0])
        print(number_reviews)

        rating_before = driver.find_element(By.CSS_SELECTOR, 'div[class="business-summary-rating-badge-view__rating"]').text

        while True:
            blocks = driver.find_elements(By.CSS_SELECTOR, 'div[class="business-reviews-card-view__review"]')
            len_b = len(blocks)
            print(len_b)
            await asyncio.sleep(3)

            if len_b == number_reviews:
                break

        datas = {
            "Дата": [],
            "Текст": [],
            "Бренд": [project] * len_b,
            "Источник": ["yandex.ru/maps"] * len_b,
            "Url": [],
            "Автор": [],
            "Оценка": [],
            "Общий Url": [url] * len_b,
            "Кол-во отзывов": [number_reviews] * len_b,
            "Оценка компании до удаления": [rating_before] * len_b
        }

        for block in blocks:
            formatted_date = block.find_element(By.CSS_SELECTOR, 'span[class="business-review-view__date"]').text
            feedback = block.find_element(By.CSS_SELECTOR, 'span[class="business-review-view__body-text"]').text
            url_answer = ""
            author = block.find_element(By.CSS_SELECTOR, 'span[itemprop="name"]').text

            star_full = block.find_elements(By.CSS_SELECTOR, 'span[class="inline-image _loaded icon business-rating-badge-view__star _full"]')
            rating = len(star_full)

            datas['Дата'].append(formatted_date)
            datas['Текст'].append(feedback)
            datas['Url'].append(url_answer)
            datas['Автор'].append(author)
            datas['Оценка'].append(rating)

        await append_data_to_sheet_scopes(service, ss_id, project, datas)

async def main_sberbank():
    service = await get_service()
    driver = await get_selenium_proxy(headless=False, proxy=False)
    driver2 = await get_selenium_proxy(headless=False, proxy=False)

    ss_id = '1FLCSWjY9vWv2Lf1hVB4BORfXK3B1tCvx85su2ZHAKyY'
    project = 'Sberbank'

    df = await read_table_id(service, ss_id, project)
    links = df['Url'].tolist()

    urls = ['https://otzovik.com/reviews/negosudarstvenniy_pensionniy_fond_sberbanka_russia_moscow/',
            'https://irecommend.ru/content/npf-sberbanka',]

    #urls = ['https://irecommend.ru/content/npf-sberbanka']

    for url in urls:
        if "otzovik" in url:
            await otzovik(service, driver, driver2, project, links, url)

        elif "irecommend.ru" in url:
            pages = 2
            source = "irecommend.ru"
            number_reviews = 54
            rating_before = 3.3

            for page in range(0, pages + 1):
                url_o = url + f"?page={page}"
                driver.get(url_o)
                print(f'\n\nStart: {url_o}')
                await asyncio.sleep(7)

                blocks = driver.find_elements(By.CSS_SELECTOR, 'div[data-type="1"]')
                #print('- 2')
                len_b = len(blocks)

                for block in blocks:
                    rating_content = block.find_elements(By.CSS_SELECTOR, 'div[class="on"]')
                    rating = len(rating_content)

                    if rating >= 4:
                        continue

                    url_answer = block.find_element(By.CSS_SELECTOR, 'a[class="reviewTextSnippet"]').get_attribute("href")
                    if url_answer in links:
                        continue

                    print("url_feedback:", url_answer)

                    feedback = await get_feedback_irec(url_answer)
                    formatted_date = block.find_element(By.CSS_SELECTOR, 'div[class="created"]').text
                    author = block.find_element(By.CSS_SELECTOR, 'div[class="authorName"]').text

                    datas = await empty_data()

                    datas['Дата'].append(formatted_date)
                    datas['Текст'].append(feedback)
                    datas["Бренд"].append(project)
                    datas["Источник"].append(source)

                    datas['Url'].append(url_answer)
                    datas['Автор'].append(author)
                    datas['Оценка'].append(rating)

                    datas["Общий Url"].append(url)
                    datas["Кол-во отзывов"].append(number_reviews)
                    datas["Оценка компании до удаления"].append(rating_before)

                    #print(datas)

                    await append_data_to_sheet_scopes(service, ss_id, project, datas)
                    await asyncio.sleep(5)

    driver.quit()
    driver2.quit()

async def banki_ru(ss_id, project):
    service = await get_service()
    links = await get_links(service, ss_id, project)
    driver = await get_selenium_proxy(headless=False, proxy=False)
    # driver2 = await get_selenium_proxy(headless=False, proxy=False)
    #
    # try:
    #     df = await read_table_id(service, ss_id, project)
    #     links = df['Url'].tolist()
    #
    # except:
    #     links = []
    #
    # url = "https://otzovik.com/reviews/banki_ru-informacionniy_portal_bankovskih_uslug/"
    # await otzovik(service, driver, driver2, project, links, url)

    url = 'https://irecommend.ru/content/bankiru'
    start_page = 6
    await get_irec(service, ss_id, project, driver, links, url, start_page, 2)

async def nlmk(project, fix_rating):
    service = await get_service()
    df = await read_table_id(service, ss_id, project)
    texts = df['Текст'].tolist()

    driver = await get_selenium_proxy(headless=False, proxy=False)


    urls = ['https://yandex.md/maps/org/novolipetskiy_metallurgicheskiy_kombinat/1037025051/reviews/?ll=39.622478%2C52.571667&z=16']

    for url in urls:
        driver.get(url)

        await asyncio.sleep(5)

        org_id = await get_id_org(url)

        while True:
            try:
                reviews_element = driver.find_element(By.CSS_SELECTOR, 'h2[class="card-section-header__title _wide"]')
                reviews_text = reviews_element.text
                number_reviews = int(reviews_text.split(" ")[0])
                print(1, number_reviews)
                break

            except:
                try:
                    reviews_element = driver.find_element(By.CSS_SELECTOR,
                                                          'h2[class="card-section-header__title"]')
                    reviews_text = reviews_element.text
                    number_reviews = int(reviews_text.split(" ")[0])
                    print(2, number_reviews)
                    break

                except:
                    await asyncio.sleep(2)

        rating_before = driver.find_element(By.CSS_SELECTOR,
                                            'div[class="business-summary-rating-badge-view__rating"]').text

        #number_reviews = 50

        while True:
            blocks = driver.find_elements(By.CSS_SELECTOR, 'div[class="business-reviews-card-view__review"]')
            len_b = len(blocks)
            print("Скрол вниз:", len_b)
            await asyncio.sleep(3)

            if len_b == number_reviews:
                break

        datas = {
            "Дата": [],
            "Текст": [],
            "Бренд": [],
            "Источник": [],
            "Url": [],
            "Автор": [],
            "Оценка": [],
            "Общий Url": [],
            "Кол-во отзывов": [],
            "Оценка компании до удаления": [],
            'Вероятность удаления': [],
            'Текст для поддержки': []
        }

        for k, block in enumerate(blocks):
            print(k)
            formatted_date = block.find_element(By.CSS_SELECTOR, 'span[class="business-review-view__date"]').text
            feedback = block.find_element(By.CSS_SELECTOR, 'span[class=" spoiler-view__text-container"]').text

            if feedback in texts:
                continue

            try:
                url_author = block.find_element(By.CSS_SELECTOR, 'a[class="business-review-view__user-icon"]').get_attribute("href")
                url_author_split = url_author.split('/')[-1]
                url_answer = f'https://yandex.md/maps/org/{org_id}/reviews?reviews%5BpublicId%5D={url_author_split}&utm_source=review'

            except:
                url_answer = ''

            author = block.find_element(By.CSS_SELECTOR, 'span[itemprop="name"]').text

            star_full = block.find_elements(By.CSS_SELECTOR,
                                            'span[class="inline-image _loaded icon business-rating-badge-view__star _full"]')
            rating = len(star_full)

            if rating > fix_rating:
                continue

            datas['Дата'].append(formatted_date)
            datas['Текст'].append(feedback)
            datas['Бренд'].append(project)
            datas['Источник'].append("yandex.ru/maps")
            datas['Url'].append(url_answer)
            datas['Автор'].append(author)
            datas['Оценка'].append(rating)
            datas['Общий Url'].append(url)
            datas['Кол-во отзывов'].append(number_reviews)
            datas['Оценка компании до удаления'].append(rating_before)

        await append_data_to_sheet_scopes(service, ss_id, project, datas)

async def tk_kit(ss_id, project):

    try:
        df_links = await read_table_id(service, ss_id, project)
        links = df_links['Url'].tolist()
    except:
        links = []
    #---------------------------Otzovik------------------------------
    driver = await get_selenium_proxy(headless=False, proxy=proxy_on)
    #driver2 = await get_selenium_proxy(headless=False, proxy=False)

    start_page = 10
    # for i in range(1,4): #вторая цифра до скольки не включительно т.е. собрать данные по 1-3 звезд
    #     await otzovik(service, driver, driver2, ss_id, project, links, i, start_page)

    url = 'https://irecommend.ru/content/transportnaya-kompaniya-kit'
    await get_irec(service, ss_id, project, driver, links, url, start_page)

async def molcom(ss_id, project):
    service = await get_service()

    url = 'https://yandex.kz/maps/org/molkom/1363951847/reviews/?ll=37.853102%2C55.981127&z=14'

    try:
        df_links = await read_table_id(service, ss_id, project)
        links = df_links['Url'].tolist()
    except:
        links = []

    await get_ya_maps(service, url, ss_id, project, links)

async def t_insurance(ss_id, project):
    service = await get_service()

    url = 'https://irecommend.ru/content/tinkoff-onlain-strakhovanie'

    try:
        df_links = await read_table_id(service, ss_id, project)
        links = df_links['Url'].tolist()
    except:
        links = []

    start_page = 0
    rating_max = 2
    driver = await get_selenium_proxy(headless=False, proxy=False)
    await get_irec(service, ss_id, project, driver, links, url, start_page, rating_max)

async def multi_pars(ss_id, project):
    service = await get_service()

    df = await read_table_id(service, ss_id, 'links')
    print(df)

    if df.empty:
        pass

    links = await get_links(service, ss_id, project)

    start_page = 0

    driver = await get_selenium_proxy(headless=False, proxy=False)
    driver2 = await get_selenium_proxy(headless=False, proxy=False)

    for k, row in df.iterrows():
        status = row['status']
        if status == 'OK!':
            continue

        url = row['link']
        print(f'\n{url}')
        rating_max = int(row['max_raiting'])

        if 'otzovik' in url:
            await pars_otzovik(service, driver, url, driver2, ss_id, project, links, rating_max, start_page)
            await append_data_to_sheet_cell(service, ss_id, 'links', 'status', k + 2, 'OK!')
            await asyncio.sleep(3)

        elif '2gis' in url:
            await pars_2gis(service, url, ss_id, project, links, rating_max)
            await append_data_to_sheet_cell(service, ss_id, 'links', 'status', k + 2, 'OK!')
            await asyncio.sleep(3)

        elif 'yandex' in url:
            await pars_ya_maps(service, driver, url, ss_id, project, links, rating_max)
            await append_data_to_sheet_cell(service, ss_id, 'links', 'status', k + 2, 'OK!')
            await asyncio.sleep(3)

        elif 'zoon' in url:
            await pars_zoon(service, driver, url, ss_id, project, links, rating_max)
            await append_data_to_sheet_cell(service, ss_id, 'links', 'status', k + 2, 'OK!')
            await asyncio.sleep(3)

        elif 'irecommend' in url:
            await pars_irec(service, driver, driver2, url, ss_id, project, links, rating_max)
            await append_data_to_sheet_cell(service, ss_id, 'links', 'status', k + 2, 'OK!')
            await asyncio.sleep(3)

        elif 'tripadvisor' in url:
            await pars_tripadvisor(service, driver, url, ss_id, project, links, rating_max)
            await append_data_to_sheet_cell(service, ss_id, 'links', 'status', k + 2, 'OK!')
            await asyncio.sleep(3)

        elif 'pravda-sotrudnikov' in url:
            await pars_pravda(service, url, ss_id, project, links)
            await append_data_to_sheet_cell(service, ss_id, 'links', 'status', k + 2, 'OK!')
            await asyncio.sleep(3)

        elif 'otzyvru' in url:
            await pars_otzyvru(service, driver, url, ss_id, project, links, rating_max)
            await append_data_to_sheet_cell(service, ss_id, 'links', 'status', k + 2, 'OK!')
            await asyncio.sleep(3)







    try:
        driver.quit()
        driver2.quit()

    except:
        pass

async def main():

    ss_id = '1Gq-veXg2d97GPwh-2MuqmUI4Af5LDoZGhdhCDJUDR-k'
    project = 'SberMedic'

    #await sberlising(ss_id, project)

    await asyncio.gather(
       review_analysis(ss_id, project),
       multi_pars(ss_id, project))

    #await review_analysis(ss_id, project, 3)
    #await banki_ru(ss_id, project)

if __name__ == '__main__':
    asyncio.run(main())
    print("OK!!!")
    


