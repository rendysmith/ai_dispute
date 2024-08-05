import asyncio
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import zlib
import base64


from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils.gs_editor import get_service, get_table_scope, pars_url
from utils.ai_module import generate_and_white
from utils.user_agent import gen_ua


current_date = datetime.now()

import os
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)
days_ago = int(os.environ.get("DAYS_AGO"))

seven_days_ago = current_date - timedelta(days=days_ago)
formatted_7date = seven_days_ago.strftime('%Y-%m-%d')

async def check_drive2(service, link, pattern, criteria, ss_id, project):
    print(link)
    links = await pars_url(service, ss_id, project)
    domen = "https://www.drive2.ru"
    headers = await gen_ua(domen)

    response = requests.get(link, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    #print(soup)

    blocks = soup.find_all("div", {"class": "c-comment"})
    print(len(blocks))

    if len(blocks) == 0:
        return



    input('OK!')











        # await generate_and_white(service=service,
        #                          url_answer=url_answer,
        #                          author=author,
        #                          formatted_date=formatted_date,
        #                          ss_id=ss_id,
        #                          project=project,
        #                          feedback=feedback,
        #                          pattern=pattern,
        #                          criteria=criteria)




# if __name__ == '__main__':
#     service = asyncio.run(get_service())
#     url = 'https://2gis.ru/tyumen/firm/70000001078903378/tab/reviews'
#     asyncio.run(check_2gis(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", "Паритет"))
#
#     print('Отметка о выполнении')
#     data = {'service_name': 'PRAVDA', 'date': time.ctime()}
#     asyncio.run(skillbox_sheet(service, '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8', 'logs', data))