import asyncio
import time

from ai_pref_react import main_react
from ai_skillbox import check_pravda, check_ocompanii
from utils.gs_editor import append_data_to_sheet_scope

from datetime import datetime

current_day_of_year = datetime.now().timetuple().tm_yday
hour = datetime.now().hour
minute = datetime.now().minute
print(f"Сегодня {current_day_of_year}-й день в году "
      f"и время {hour}:{minute}")

if __name__ == '__main__':
    asyncio.run(main_react())
    data = {'service_name': 'PMEF', 'date': time.ctime()}
    asyncio.run(append_data_to_sheet_scope('1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8', 'logs', data))

    if hour == 6 and 0 <= minute < 15:
        if current_day_of_year % 2 == 0:
            asyncio.run(check_pravda())
            data = {'service_name': 'Skillbox pravda', 'date': time.ctime()}
            asyncio.run(append_data_to_sheet_scope('1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8', 'logs', data))

        else:
            asyncio.run(check_ocompanii())
            data = {'service_name': 'Skillbox ocompanii', 'date': time.ctime()}
            asyncio.run(append_data_to_sheet_scope('1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8', 'logs', data))

    print('OK!')
