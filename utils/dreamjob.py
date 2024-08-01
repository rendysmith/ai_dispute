import asyncio
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time

from utils.gs_editor import get_service, get_table_scope
from utils.ai_module import generate_and_white
#from ai_skillbox import pars_url, generator
import textwrap

current_date = datetime.now()

async def pars_url(service, SS_ID, R_N):
    df = await get_table_scope(service, SS_ID, R_N)
    links = df['Link'].to_list()
    return links

async def convert_date(month):
    months = {
        'январь': 1,
        'февраль': 2,
        "март": 3,
        "апрель": 4,
        "май": 5,
        "июнь": 6,
        "июль": 7,
        "август": 8,
        "сентябрь": 9,
        "октябрь": 10,
        "ноябрь": 11,
        "декабрь": 12
    }
    return months[month]

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

async def check_dreamjob(service, link, pattern, criteria, ss_id, project):
    links = await pars_url(service, ss_id, project)
    print(links)

    unix_time = str(int(time.time() * 1000))

    pages = ['1', '2.1', '3.2666666666666666']

    for page in pages:
        url = f'{link}?erfrp%5BlastParam%5D=&erfrp%5Bfrom_vacancy%5D=&sort=-created_at&page={page}&_={unix_time}'
        print(url)

        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        #print(soup)

        blocks = soup.find_all('div', {"class": 'review', 'data-partly': 'short'})
        print(len(blocks))

        for block in blocks:
            print('\n*******************************************')
            url_answer = block.find('a', {'class': 'bt bt--32 bt--primary-link icon-copy'}).get('href')

            if url_answer in links:
                print('Отзыв уже есть в таблице')
                continue

            date = block.find_next('div', {'class': 'review__header-date'}).text
            #print(date)

            date_spl = date.split('\xa0')
            #print(date_spl)
            month = await convert_date(date_spl[0])
            target_date = datetime(int(date_spl[1]), month, 31)
            print(target_date)

            if (current_date - target_date) > timedelta(days=30):
                print(f'--- Отзыв старше 30 дней = {date}.')
                continue
                # return  # Выход если очень старые отзывы

            answer_title = block.find('h3', class_='review__answer-title')
            if answer_title:
                print("Найден заголовок ответа:", answer_title.text)
                continue

            author = block.find('h2', {'class': 'review__header-title'}).text.strip()
            print(author)

            title_div_plus = soup.find('div', class_='review__title review__gap')
            plus_title = title_div_plus.text

            title_plus = await get_content(title_div_plus)

            if title_plus:
                plus = title_plus

            #title_div_minus = soup.find('div', class_='review__title')
            title_div_minus = soup.find('div', class_='review__title', string='Что можно было бы улучшить')
            minus_title = title_div_minus.text

            title_minus = await get_content(title_div_minus)

            if title_minus:
                minus = title_minus

            feedback = f"""
            {plus_title}:
            {plus}
            {minus_title}:
            {minus}
            """
            feedback = textwrap.dedent(feedback)

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

        time.sleep(5)