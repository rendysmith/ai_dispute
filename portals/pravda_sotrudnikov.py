import asyncio
import random

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time

from utils.gs_editor import get_table_scope
from utils.ai_module import generate_and_white
#from ai_skillbox import pars_url, generator
import textwrap

current_date = datetime.now()

import os
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)
days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

async def pars_url(service, SS_ID, R_N):
    df = await get_table_scope(service, SS_ID, R_N)
    links = df['Link'].to_list()
    return links

async def check_pravda(service, link, pattern, criteria, ss_id, project):
    ts = random.randint(5, max_sec)
    print(f'Wait {ts} sec...')
    await asyncio.sleep(ts)

    url = f'https://pravda-sotrudnikov.ru/company/{link}?sort=date'
    print(url)
    links = await pars_url(service, ss_id, project)

    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    last_page = 1
    li = soup.find_all('li')
    for l in li:
        txt = l.text
        if txt.isdigit():
            last_page = int(txt)

    #print(last_page)

    for i in range(last_page):
        url_page = url + f'&page={i+1}'
        print(url_page)

        response = requests.get(url_page)
        soup = BeautifulSoup(response.text, 'html.parser')
        #print(soup)

        blocks = soup.find_all('div', class_='company-reviews-list-item')
        if len(blocks) > 0:
            for block in blocks:
                button = block.find('a', class_='btn btn-yellow show-answers-button')
                answer = button.text

                url_answer = 'https://pravda-sotrudnikov.ru' + button.get('href')
                if url_answer in links:
                    print(f'{url_answer}\nНа этот отзыв уже есть реакция!\n')
                    continue

                if answer == 'Ответить':
                    date_str = block.find('div', class_='company-reviews-list-item-date').text.strip()
                    date = datetime.strptime(date_str, "%H:%M %d.%m.%Y")
                    # unix_time = date.timestamp()
                    if (current_date - date) > timedelta(days=30):
                        print(f'--- Отзыв старше 30 дней = {date}.')
                        #continue
                        return #Выход если очень старые отзывы

                    else:
                        print(f'+++ Отзыв в пределах 30 дней = {date}\n'
                              f'{(current_date - date)} > {timedelta(days=days_ago)}')

                    formatted_date = date.strftime("%d.%m.%Y")

                    author = block.find('div', class_='company-reviews-list-item-name').text.split('\t')
                    cleaned_lines = [line.replace('\t', '').replace('\n', '') for line in author if line != '' and line != '\n']
                    author = ' '.join(cleaned_lines)
                    #print(author)

                    conteiners = block.find_all('div', {'class': 'company-reviews-list-item-text-container'})

                    plus_title = conteiners[0].find('div', {'class': 'company-reviews-list-item-text-title'}).text
                    plus = conteiners[0].find('div', {'class': 'company-reviews-list-item-text-message'}).text.strip()

                    minus_title = conteiners[1].find('div', {'class': 'company-reviews-list-item-text-title'}).text
                    minus = conteiners[1].find('div', {'class': 'company-reviews-list-item-text-message'}).text.strip()

                    feedback = f"""
                    {plus_title}:
                    {plus}
                    {minus_title}:
                    {minus}
                    """
                    feedback = textwrap.dedent(feedback)

                    # plus_title = block.find('div', {'class': 'company-reviews-list-item-text-title'}).text
                    # minus_title = block.find('div', {'class': 'company-reviews-list-item-text-title'}).text
                    #
                    # messages = block.find_all('div', class_='company-reviews-list-item-text-message')
                    #
                    # plus = messages[0].text.split('\n')
                    # cleaned_lines = [line.replace('\t', '') for line in plus]
                    # plus = '\n'.join(cleaned_lines)
                    #
                    # minus = messages[1].text.split('\n')
                    # cleaned_lines = [line.replace('\t', '') for line in minus]
                    # minus = '\n'.join(cleaned_lines)

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

# if __name__ == '__main__':
#     service = asyncio.run(get_service())
#     asyncio.run(check_pravda(service))
#
#     print('Отметка о выполнении')
#     data = {'service_name': 'PRAVDA', 'date': time.ctime()}
#     asyncio.run(skillbox_sheet(service, '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8', 'logs', data))