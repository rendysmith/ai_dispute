import asyncio
import os
import re
import time

from datetime import datetime, timedelta

from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

from utils.ai_module import get_answer_ai
from utils.constants import TABLES_LIST
from utils.gs_editor import get_table_scope, get_service, write_log_sheet, append_data_to_sheet_cell
from utils.central_module import get_articles

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

async def ai_generate_article_economy(service, auth, project):
    now_time = datetime.now()
    current_date = now_time.strftime("%d.%m.%Y")
    print(current_date)

    next_month = now_time + timedelta(days=30)  # Прибавляет 30 дней
    worksheet_name = next_month.strftime("%b_%Y") + '_economy'
    print(worksheet_name)

    worksheet_name_2 = now_time.strftime("%b_%Y") + '_economy'
    print(worksheet_name_2)

    df_aricles = await get_articles('https://dzen.ru/topic/economy?tab=articles')

    worktable_id = TABLES_LIST[project][0]

    worksheet_names = [worksheet_name, worksheet_name_2]

    for worksheet_name in worksheet_names:
        try:
            df = await get_table_scope(service, worktable_id, worksheet_name)

        except:
            print('Next tab...')
            continue

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