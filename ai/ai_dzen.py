import asyncio
import os
import re
import time

from datetime import datetime, timedelta
import pandas as pd
from bs4 import BeautifulSoup
import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

from utils.ai_module import get_answer_ai
from utils.constants import TABLES_LIST
from utils.gs_editor import get_table_scope, get_service, write_log_sheet, append_data_to_sheet_cell



dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

username = os.environ.get("HOST_USERNAME")
password = os.environ.get("HOST_PASSWORD")
auth = HTTPBasicAuth(username, password)

prompt_economy = """
Представь, что ты копирайтер, пишущий статьи на экономические темы
Твоя задача написать статью на тему {subject}
Ты должен соблюдать главные принципы при написании статьи
Главный принцип: Контент должен быть полезным, доступным и уникальным.
Нарушения ведут к ограничениям:
Ограничение показа: Публикация видна только подписчикам.
Блокировка канала: Публикации полностью скрыты.
Отключение монетизации: Доход от публикаций не поступает.
Что запрещено:
Азартные игры, лотереи, стимулирующие мероприятия: Запрещена любая реклама и пропаганда участия.
Дублированный контент: Повторная публикация материалов.
Заимствованный контент: Публикация чужого контента без указания авторства.
Запрещённые товары и услуги: Наркотики, оружие, торговля людьми и т.д.
Искусственное завышение показателей: Накрутка просмотров, дочитываний, подписчиков.
Кликбейт: Заголовки и карточки, обманывающие ожидания пользователей.
Ложная информация и фейки: Публикация недостоверных фактов.
Незаконная информация: Призывы к противоправным действиям, нарушению прав, размещение ссылок на нелегальный контент.
Неприятное изображение на карточке: Фотографии, вызывающие отвращение (насекомые, туши животных, и т.д.)
Оскорбления и нападки: Грубые высказывания, травля, запугивание.
Откровенный контент: Материалы эротического характера.
Происшествия и трагедии: Спекуляция на чужом горе.
Сниженная лексика: Обилие нецензурной лексики и жаргонизмов.
Спам: Распространение нерелевантной информации.
Товары и услуги, вредящие здоровью: Реклама и пропаганда табака, алкоголя, вейпов.
Шокирующий контент: Изображения насилия, трупов, травм.
Язык вражды и пропаганда насилия: Разжигание ненависти, дискриминация, призывы к насилию.
Что разрешено с ограничениями:
Медицина и фармацевтика: Допустимы информационные материалы с опорой на доказательную медицину, без призывов к самолечению и рекламы конкретных препаратов.
Важно помнить:
Указывайте авторство при использовании чужих материалов.
Не используйте кликбейт и шокирующий контент на карточках публикаций.
Будьте вежливы и уважайте других пользователей.
Перед запуском рекламы убедитесь, что материал соответствует правилам Дзена.
** Соблюдайте правила Дзена, создавайте качественный и интересный контент!**
"""

async def parse_read_count(text):
    # Извлечение числа прочтений с учетом формата с запятыми и суффиксом "K"
    match = re.search(r'(\d+(?:,\d+)?K?) прочтений?', text)
    if match:
        count = match.group(1).replace(',', '.')
        if 'K' in count:
            count = float(count.replace('K', '')) * 1000
        return int(count)
    return 0

async def get_articles():
    url = 'https://dzen.ru/thematics/economy?bookmark_desktop=true'

    response = requests.get(url)
    html_content = response.text

    # Создаем объект BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Пример: получение заголовка страницы
    title = soup.title
    print('Заголовок страницы:', title.text.strip())

    cards = soup.find_all('article', class_='desktop2--card-part-wrapper__cardPartWrapper-3S card-article')
    print('Len cards =', len(cards))

    if len(cards) == 0:
        cards = soup.find_all('article', {"aria-label":'Карточка этажа', "data-testid":"floor-image-card"})
        print('Len cards =', len(cards))

    if len(cards) == 0:
        cards = soup.find_all('article', {"data-testid":"floor-image-card"})
        print('Len cards =', len(cards))

    datas = []

    for card in cards:
        card_title = card.find('div', class_='desktop2--card-part-title__title-dF desktop2--card-part-title__l-1t').text
        print(card_title)

        numbers = card.find('div', class_='desktop2--meta__meta-3m').text.split('.')
        print(numbers)

        views = numbers[0]
        int_views = await parse_read_count(views)
        print(int_views)

        datas.append([card_title, int_views])

    df = pd.DataFrame(datas)
    df = df.sort_values(by=1, ascending=False).head(3).reset_index(drop=True)
    print(df)
    return df


async def ai_generate_article_economy(service, auth, project):
    now_time = datetime.now()
    current_date = now_time.strftime("%d.%m.%Y")
    print(current_date)

    next_month = now_time + timedelta(days=30)  # Прибавляет 30 дней
    worksheet_name = next_month.strftime("%b_%Y") + '_economy'
    print(worksheet_name)

    worksheet_name_2 = now_time.strftime("%b_%Y") + '_economy'
    print(worksheet_name_2)

    df_aricles = await get_articles()

    worktable_id = TABLES_LIST[project][0]

    try:
        df = await get_table_scope(service, worktable_id, worksheet_name)

    except:
        df = await get_table_scope(service, worktable_id, worksheet_name_2)
        worksheet_name = worksheet_name_2

    print(worktable_id, worksheet_name)

    print(df)

    for idx, row in df.iterrows():
        date = row['Date']

        if current_date != date:
            print('Next day...')
            continue

        top_number = int(row['Top_number'])
        print(top_number)

        subject = df_aricles.loc[top_number - 1, 0]
        print("Subject:", subject)

        prompt = prompt_economy.format(subject=subject)
        result = await get_answer_ai(auth, prompt)

        await append_data_to_sheet_cell(service, worktable_id, worksheet_name, 'Result', idx + 2, result)
        print(f'{worksheet_name} - OK!')




async def main_article_eco():
    project = 'Article_eco'
    service = await get_service()
    await ai_generate_article_economy(service, auth, project)

    data = {'service_name': project, 'date': time.ctime()}
    await write_log_sheet(service, '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8', 'logs', data)

if __name__ == '__main__':
    asyncio.run(main_article_eco())