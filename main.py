import asyncio

from datetime import datetime

from ai.ai_rbi_reactions import main_rbi #Обработка данных RBI
from portals.brandanalytics import main_ba #Анализ на сайте brandanalytic

from ai.ai_article import main_article #Генерация развлекательных статей
from ai.ai_dzen import main_article_eco #Генерация экономических статей

from load_distribution import main_distribution #Распределение сервером на масштабировании

from scaling_service import main_zoom #Запуск парсинга масштабирования

from portals.irecommend import main_irecommend #Парсинг только irecommend
from portals.portal_otzovik import main_otzovik #otzovik
from portals.portal_ya import main_ya_maps #main ya_maps
from portals.portal_sravni import main_sravni

from scaling_antibot import main_scaling

async def main_total():
    now = datetime.now()
    now_hour = now.hour
    now_weekday = now.weekday()

    #every hour
    await main_rbi()
    await asyncio.sleep(60)

    # every day
    if now_hour == 5:
        await main_article()

    #2 times in week
    if now_weekday in [1, 4] and now_hour == 1:
        pass

if __name__ == '__main__':
    asyncio.run(main_distribution())
    print('OK!')
