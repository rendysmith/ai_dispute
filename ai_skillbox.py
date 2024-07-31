import asyncio

from bs4 import BeautifulSoup
import requests

from selenium import webdriver

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

import os, re

import random
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

from utils.gs_editor import get_table_scope, append_data_to_sheet_scope
from utils.ai_module import get_answer_ai

current_date = datetime.now()

abspath = os.path.dirname(os.path.abspath(__file__))

SS_ID = '1A73rT27Sa2Au5Bsb8v2u_C-ttDwJAYg_rY27CUfzdbw'
R_N = 'Skillbox'

def prompt_txt(review):
    return f"""             
    Ты официальный представитель компании Skillbox. 
    Ты должен прочитать отзыв о своей компании от бывшего или текущего работника компании, и в вежливой и корректной форме ответить на отзыв.       
    Ты должен понять по тексту от чего лица сообщение, от мужского или женского.
    Используй только официальное обращение к пользователю.
    Обрати внимание на имя пользователя, пиши обращение по имени - если оно конкретно указано или обращайся без конкретного имени.
    НЕ использую какого либо имени когда здороваешься с пользователем,
    НЕ обращайся к пользователю по профессии.
    НЕ используй например 'Уважаемый (ая) Аноним,', 'Уважаемый/ая Аноним,' и т.п. - вместо этого пиши просто 'Здравствуйте.' и т.п.
    НЕ используй '[Ваше имя]' или '(Твоё имя)' и т.п. в тексте, текст должен быть окончательно сформированным.  
    ВАЖНО! Не придумывай пользователю имена, если имя не указано обращайся общими фразами. 
    Завершай сообщение всегда фразой 'С уважением, Команда Skillbox'

    Текущий отзыв пользователя:
    {review}

    Перед решением задачи, прочитай задание еще раз.
    """

async def generator(service, url_answer, author, date, plus, minus):
    review = f"""
Плюсы в работе:
{plus}

Отрицательные стороны:
{minus}
    """
    prompt = prompt_txt(review)

    start_time = time.time()

    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    load_dotenv(dotenv_path)

    username = os.environ.get("HOST_USERNAME")
    password = os.environ.get("HOST_PASSWORD")
    auth = HTTPBasicAuth(username, password)
    result = await get_answer_ai(auth, prompt)

    print(f'TIMER {round(time.time() - start_time, 2)}')

    data = {
        'Link': url_answer,
        'Author': author,
        'Date': date,
        'Review': review,
        'Results': result,

    }

    status = await append_data_to_sheet_scope(service, SS_ID, R_N, data)
    print(status)

# async def pars_url(service):
#     df = await get_table_scope(service, SS_ID, R_N)
#     links = df['Link'].to_list()
#     return links




