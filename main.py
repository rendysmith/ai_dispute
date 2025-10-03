import asyncio

from datetime import datetime

from scaling_service import main_zoom #Функция опроса всех порталов

from ai.ai_brandanalytics import main_ba #Генерация данных из BA
from ai.ai_rbi_reactions import main_rbi #Обработка данных RBI
from ai.ai_desport import main_desport #Ответы на комменты Desport
from ai.ai_desport_cards import main_desport_cards #Генерация отзывов


from ai.ai_article import main_article #Генерация развлекательных статей
from ai.ai_dzen import main_article_eco #Генерация экономических статей
from ai.ai_sidorin_positive import main_sidorin #Проверка отзывов для их оспаривания.

from portals.portal_otzovik import main_otzovik #Отдельная функция для отзовика
from portals.irecommend import main_irecommend #Отдельная функция для irec
from portals.portal_sravni import main_sravni
from portals.portal_ya import main_ya_maps

from portals.portal_2gis import main_2gis_sberstrem

from products.alfapet import main_alfa

from load_distribution import main_distribution #Распределение сервером на масштабировании

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
