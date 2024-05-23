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

from utils.gs_editor import get_table_scope, append_data_to_sheet_scope
from utils.ai_module import get_answer_gemini, get_answer_gpt

current_date = datetime.now()

abspath = os.path.dirname(os.path.abspath(__file__))


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

async def generator(url_answer, author, date, plus, minus):
    review = f"""
Плюсы в работе:
{plus}

Отрицательные стороны:
{minus}
    """
    prompt = prompt_txt(review)
    engine_gemini = 'gemini-pro'
    engine_gpt = 'gpt-3.5-turbo'

    start_time = time.time()

    results = await asyncio.gather(
        get_answer_gemini(prompt, engine_gemini),
        get_answer_gpt(prompt, engine_gpt)
    )
    result_gemini = results[0]
    result_gpt = results[1]

    print(f'TIMER {round(time.time() - start_time, 2)}')

    data = {
        'Link': url_answer,
        'Author': author,
        'Date': date,
        'Review': review,
        f'Результат от {engine_gemini}': result_gemini,
        f'Результат от {engine_gpt}': result_gpt
    }

    status = await append_data_to_sheet_scope(SS_ID, R_N, data)
    print(status)

async def pars_url():
    SS_ID = '1A73rT27Sa2Au5Bsb8v2u_C-ttDwJAYg_rY27CUfzdbw'
    R_N = 'Skillbox'
    df = await get_table_scope(SS_ID, R_N)
    links = df['Link'].to_list()
    return links



async def check_ocompanii():
    url = 'https://ocompanii.net/company/information.php?cid=764047'
    links = await pars_url()
    cor_path = os.path.abspath(os.curdir)
    print(cor_path)

    chrome_options = Options()
    #chrome_options.add_argument(fr"user-data-dir={cor_path}/Skillbox")
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)

    driver.get(url)
    time.sleep(5)

    hrefs = driver.find_elements(By.CSS_SELECTOR, "div[id]")
    print(len(hrefs))

    id_reviews = []
    for href in hrefs:
        if href.get_attribute('class'):
            continue

        id_attr = href.get_attribute('id')

        if 'comment_preview_' in id_attr:
            #print(id_attr)
            match1 = re.search(r'comment_preview_(\d+)', id_attr)

            if match1:
                id_review = match1.group(1)
                id_reviews.append(id_review)

    print(id_reviews)

    blocks = driver.find_elements(By.CSS_SELECTOR, "div[class='col-sm-12 col-md-12']")
    print('Blocks =', len(blocks))

    cont = False
    for block in blocks:
        a_style = block.find_elements(By.CSS_SELECTOR, "a[style]")
        print('Len Style =', len(a_style))

        if len(a_style) == 0:
            continue

        url_answer = a_style[0].get_attribute('href')
        print('Url:', url_answer)

        if url_answer in links:
            print(f'{url_answer}\nНа этот отзыв уже есть реакция!\n')
            continue

        match1 = re.search(r'id=(\d+)', url_answer)

        if match1:
            id_review = match1.group(1)
            # print(type(id_review))
            # print(id_review)

            if id_review in id_reviews:
                continue

        author = block.find_element(By.CSS_SELECTOR, "span[itemprop='author']").text
        #print(author)

        formatted_date = 'No Date'
        spans = block.find_elements(By.CSS_SELECTOR, "span")
        for span in spans:
            #print(span.text)
            try:
                date = datetime.strptime(span.text, "%Y-%m-%d %H:%M:%S")

            except Exception as ex:
                # print('Error =', span.text)
                # print(ex)
                continue

            #unix_time = date.timestamp()
            if (current_date - date) > timedelta(days=30):
                print(f'--- Отзыв старше 30 дней. = {date}\n')
                cont = True

            else:
                print(f'+++ Отзыв в пределах 30 дней = {date}\n'
                      f'{current_date - date} > {timedelta(days=30)}')

            formatted_date = date.strftime("%d.%m.%Y")
            #print(formatted_date)

        if cont:
            cont = False
            continue

        time.sleep(3)
        click_more = block.find_element(By.CSS_SELECTOR, "em")

        #element = driver.find_element_by_id('id_of_your_element')
        driver.execute_script("arguments[0].click();", click_more)

        #wait = WebDriverWait(driver, 10)
        #click_more = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "em")))

        #click_more.click()
        print('Click!')

        time.sleep(3)

        messages = block.find_elements(By.CSS_SELECTOR, "div[id]")

        for massage in messages:
            if 'plus' in massage.get_attribute('id'):
                plus = massage.text.replace('<<Скрыть', '')

            if 'minus' in massage.get_attribute('id'):
                minus = massage.text.replace('<<Скрыть', '')

        print(plus)
        print(minus)

        await generator(url_answer, author, formatted_date, plus, minus)
        time.sleep(5)

async def check_pravda():
    url = 'https://pravda-sotrudnikov.ru/company/skillbox'
    links = await pars_url()

    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    li = soup.find_all('li')
    for l in li:
        txt = l.text

        if txt.isdigit():
            last_page = int(txt)

    #print(last_page)

    for i in range(last_page):
        url_page = url + f'?page={i+1}'
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
                        continue

                    else:
                        print(f'+++ Отзыв в пределах 30 дней = {date}\n'
                              f'{(current_date - date)} > {timedelta(days=30)}')

                    formatted_date = date.strftime("%d.%m.%Y")
                    input()

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

                    await generator(url_answer, author, formatted_date, plus, minus)

        time.sleep(5)




