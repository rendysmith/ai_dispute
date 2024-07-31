import asyncio
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time

from utils.gs_editor import get_service, get_table_scope
from utils.ai_module import generate_and_white
#from ai_skillbox import pars_url, generator

current_date = datetime.now()

async def pars_url(service, SS_ID, R_N):
    df = await get_table_scope(service, SS_ID, R_N)
    links = df['Link'].to_list()
    return links

async def check_pravda(service, link, pattern, criteria, SS_ID, project):
    url = f'https://pravda-sotrudnikov.ru/company/{link}?sort=date'
    links = await pars_url(service, SS_ID, project)

    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
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

                if answer == 'Ответить':
                    author = block.find('div', class_='company-reviews-list-item-name').text.split('\t')

                    date_str = block.find('div', class_='company-reviews-list-item-date').text.strip()
                    date = datetime.strptime(date_str, "%H:%M %d.%m.%Y")
                    # unix_time = date.timestamp()
                    if (current_date - date) > timedelta(days=30):
                        print(f'--- Отзыв старше 30 дней = {date}.')
                        #continue
                        return #Выход если очень старые отзывы

                    else:
                        print(f'+++ Отзыв в пределах 30 дней = {date}\n'
                              f'{(current_date - date)} > {timedelta(days=30)}')

                    formatted_date = date.strftime("%d.%m.%Y")

                    #print(name)
                    cleaned_lines = [line.replace('\t', '').replace('\n', '') for line in author if line != '' and line != '\n']
                    #print(cleaned_lines)
                    author = ' '.join(cleaned_lines)
                    #print(author)

                    url_answer = 'https://pravda-sotrudnikov.ru' + button.get('href')

                    if url_answer in links:
                        print(f'{url_answer}\nНа этот отзыв уже есть реакция!\n')
                        continue

                    messages = block.find_all('div', class_='company-reviews-list-item-text-message')

                    plus = messages[0].text.split('\n')
                    cleaned_lines = [line.replace('\t', '') for line in plus]
                    plus = '\n'.join(cleaned_lines)

                    minus = messages[1].text.split('\n')
                    cleaned_lines = [line.replace('\t', '') for line in minus]
                    minus = '\n'.join(cleaned_lines)

                    text = f"""
                    Ты официальный представить компании '{project}'
                    Твоя задача прочитать комментарий о компании:
                    -----------Начало комментария--------------
                    Плюсы:
                    {plus}
                    Минусы:
                    {minus}
                    ----------Конец комментария----------------
                    и на основании шаблонов, составить отзыв
                    ----------Начало шаблонов -----------------
                    {pattern}
                    ----------Конец шаблонов ------------------
                    Необходимо учитывать следующее:
                    {criteria}
                    """

                    prompt = text.format(project, plus, minus, pattern, criteria)

                    #await generate_and_white(service, url_answer, author, formatted_date, prompt)
                    await generate_and_white(service, url_answer, author, formatted_date, prompt, SS_ID, project)

        time.sleep(5)

# if __name__ == '__main__':
#     service = asyncio.run(get_service())
#     asyncio.run(check_pravda(service))
#
#     print('Отметка о выполнении')
#     data = {'service_name': 'PRAVDA', 'date': time.ctime()}
#     asyncio.run(skillbox_sheet(service, '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8', 'logs', data))