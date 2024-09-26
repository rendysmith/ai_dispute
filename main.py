import asyncio

from datetime import datetime

from ai.ai_rbi_reactions import main_rbi
from ai.ai_article import main_article
from scaling_service import main_zoom
from load_distribution import main_distribution

from portals.brandanalytics import check_ba

now = datetime.now()
now_hour = now.hour
now_weekday = now.weekday()

async def main_total():
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
    asyncio.run(main_total())
    print('OK!')
