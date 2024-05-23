import asyncio

from ai_pref_reactions import main_react
from ai_skillbox import check_pravda, check_ocompanii

from datetime import datetime

current_day_of_year = datetime.now().timetuple().tm_yday
hour = datetime.now().hour
minute = datetime.now().minute
print(f"Сегодня {current_day_of_year}-й день в году и {minute}")

if __name__ == '__main__':
    asyncio.run(main_react())

    if hour == 6 and 0 < minute <= 15:

        if current_day_of_year % 2 == 0:
            asyncio.run(check_pravda())

        else:
            asyncio.run(check_ocompanii())

    print('OK!')

