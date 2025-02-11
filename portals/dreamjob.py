import asyncio
import random

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time

from utils.central_module import get_local_ip, get_hpo
from utils.gs_editor import get_service, get_table_scope, pars_url
from utils.ai_module import generate_and_white
#from ai_skillbox import pars_url, generator
import textwrap

from utils.user_agent import get_soup
from utils.constants import months

current_date = datetime.now()

import os
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)
days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

# local_ip = asyncio.run(get_local_ip())
# if '176.124.192' in local_ip:
#     headless = True
#     proxy_on = True
#     only_text = False
#
# else:
#     print(f'local_ip DJ: {local_ip}')
#     headless = False
#     proxy_on = False
#     only_text = False

async def get_raiting(soup):
    # soup = await get_soup(top_url)
    # if not soup:
    #     return None, None

    #общий рейтинг
    total_rating = soup.find('div', {"class": 'dashboard__grade-total'}).text
    total_rating = float(total_rating.replace(',', '.'))

    #общее кол-во отзывов
    try:
        total_reviews = soup.find('span', {"class": 'company-header__tab-count'}).text
        total_reviews = int(total_reviews.replace(' ', ''))

    except:
        total_reviews = soup.find('span', {"class": 'tabs__count'}).text
        total_reviews = int(total_reviews)

    return total_reviews, total_rating

async def get_content(title_div):
    if title_div:
        # Получаем родительский элемент
        parent = title_div.parent

        # Ищем текст непосредственно после div
        content = ''
        for element in title_div.next_siblings:
            if isinstance(element, str) and element.strip():
                content = element.strip()
                break
            elif element.name == 'div':  # Останавливаемся, если встречаем следующий div
                break

        if content:
            return content
        else:
            print("Текст не найден")
            return None
    else:
        print("Нужный div не найден")
        return None

async def get_full_feedback(block):
    # title_div_plus = soup.find('div', class_='review__title review__gap')
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

    feedback = f"""
          {plus_title}:
          {plus}
          {minus_title}:
          {minus}
          """
    # print(feedback)
    return textwrap.dedent(feedback)

async def check_dreamjob(service, link, pattern, criteria, ss_id, project):
    print(link)

    links = await pars_url(service, ss_id, project)
    #print(links)

    unix_time = str(int(time.time() * 1000))

    pages = ['1', '2.1', '3.2666666666666666']

    for page in pages:
        url = f'{link}?erfrp%5BlastParam%5D=&erfrp%5Bfrom_vacancy%5D=&sort=-created_at&page={page}&_={unix_time}'
        print(url)

        headless, proxy_on, only_text = await get_hpo()
        soup = await get_soup(url, proxy=proxy_on)
        if not soup:
            continue

        blocks = soup.find_all('div', {"class": 'review', 'data-partly': 'short'})
        print('Len:', len(blocks))
        if len(blocks) == 0:
            return None

        for block in blocks:
            print('\n*******************************************')
            url_answer = block.find('a', {'class': 'bt bt--32 bt--primary-link icon-copy'}).get('href')
            if not url_answer:
                url_answer = block.find('a', role='button', tabindex='0').get('href')

            if not url_answer:
                url_answer = block.find('a', tabindex='0').get('href')

            print(url_answer)
            if url_answer in links:
                print('Отзыв уже есть в таблице')
                continue

            print(url_answer)

            date = block.find_next('div', {'class': 'review__header-date'}).text
            #print(date)

            date_spl = date.split('\xa0')

            month = months[date_spl[0]]

            last_day = 31
            while True:
                try:
                    target_date = datetime(int(date_spl[1]), month, last_day)
                    print(target_date)
                    break

                except:
                    last_day -= 1

            if (current_date - target_date) > timedelta(days=days_ago):
                print(f'--- Отзыв старше {days_ago} дней = {date}.')
                continue
                # return  # Выход если очень старые отзывы

            answer_title = block.find('h3', class_='review__answer-title')
            if answer_title:
                print("Найден заголовок ответа:", answer_title.text)
                continue

            author = block.find('h2', {'class': 'review__header-title'}).text.strip()
            #print(author)

            feedback = await get_full_feedback(block)

            #print('///////////////')
            #print(url_answer)
            #print(feedback)
            #input()

            formatted_date = target_date.strftime("%d.%m.%Y")

            #await generate_and_white(service, url_answer, author, formatted_date, prompt)
            await generate_and_white(service=service,
                                     url_answer=url_answer,
                                     author=author,
                                     formatted_date=formatted_date,
                                     ss_id=ss_id,
                                     project=project,
                                     feedback=feedback,
                                     pattern=pattern,
                                     criteria=criteria)

async def main():
    service = await get_service()

    url = 'https://yandex.ru/maps/org/artstudio_moskovsky/125846534919/?ll=30.329628%2C59.907103&mode=search&sll=30.301828%2C59.912472&sspn=0.022573%2C0.006756&text=Artstudio%20Moskovsky&z=14.86'
    url = 'https://dreamjob.ru/employers/41950?review_id=2832885'
    url = 'https://dreamjob.ru/employers/41950'
    url = 'https://dreamjob.ru/employers/50604'
    url = 'https://dreamjob.ru/employers/58176'



    await check_dreamjob(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", 'Петрович')

if __name__ == '__main__':
    asyncio.run(main())
