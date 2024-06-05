import asyncio
import requests
import os, re

from bs4 import BeautifulSoup

from pyvirtualdisplay import Display
from selenium import webdriver

#from selenium.webdriver.support.ui import WebDriverWait
#from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
#from webdriver_manager.chrome import ChromeDriverManager

#from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
#from selenium.webdriver.common.keys import Keys

from datetime import datetime, timedelta
import time

from utils.gs_editor import skillbox_sheet, get_service
from ai_skillbox import pars_url, generator

current_date = datetime.now()

abspath = os.path.dirname(os.path.abspath(__file__))
cor_path = os.path.abspath(os.curdir)

# async def check_ocompanii_old():
#     url = 'https://ocompanii.net/company/information.php?cid=764047'
#
#     links = await pars_url()
#     cor_path = os.path.abspath(os.curdir)
#     print(cor_path)
#
#     chrome_options = Options()
#     #chrome_options.add_argument(fr"user-data-dir={cor_path}/Skillbox")
#     chrome_options.add_argument("--headless")
#     driver = webdriver.Chrome(options=chrome_options)
#
#     driver.get(url)
#     time.sleep(5)
#
#     hrefs = driver.find_elements(By.CSS_SELECTOR, "div[id]")
#     print(len(hrefs))
#
#     id_reviews = []
#     for href in hrefs:
#         if href.get_attribute('class'):
#             continue
#
#         id_attr = href.get_attribute('id')
#
#         if 'comment_preview_' in id_attr:
#             #print(id_attr)
#             match1 = re.search(r'comment_preview_(\d+)', id_attr)
#
#             if match1:
#                 id_review = match1.group(1)
#                 id_reviews.append(id_review)
#
#     print(id_reviews)
#
#     blocks = driver.find_elements(By.CSS_SELECTOR, "div[class='col-sm-12 col-md-12']")
#     print('Blocks =', len(blocks))
#
#     cont = False
#     for block in blocks:
#         a_style = block.find_elements(By.CSS_SELECTOR, "a[style]")
#         print('Len Style =', len(a_style))
#
#         if len(a_style) == 0:
#             continue
#
#         url_answer = a_style[0].get_attribute('href')
#         print('Url:', url_answer)
#
#         if url_answer in links:
#             print(f'{url_answer}\nНа этот отзыв уже есть реакция!\n')
#             continue
#
#         match1 = re.search(r'id=(\d+)', url_answer)
#
#         if match1:
#             id_review = match1.group(1)
#             # print(type(id_review))
#             # print(id_review)
#
#             if id_review in id_reviews:
#                 continue
#
#         author = block.find_element(By.CSS_SELECTOR, "span[itemprop='author']").text
#         #print(author)
#
#         formatted_date = 'No Date'
#         spans = block.find_elements(By.CSS_SELECTOR, "span")
#         for span in spans:
#             #print(span.text)
#             try:
#                 date = datetime.strptime(span.text, "%Y-%m-%d %H:%M:%S")
#
#             except Exception as ex:
#                 # print('Error =', span.text)
#                 # print(ex)
#                 continue
#
#             #unix_time = date.timestamp()
#             if (current_date - date) > timedelta(days=30):
#                 print(f'--- Отзыв старше 30 дней. = {date}\n')
#                 cont = True
#
#             else:
#                 print(f'+++ Отзыв в пределах 30 дней = {date}\n'
#                       f'{current_date - date} > {timedelta(days=30)}')
#
#             formatted_date = date.strftime("%d.%m.%Y")
#             #print(formatted_date)
#
#         if cont:
#             cont = False
#             continue
#
#         time.sleep(3)
#         click_more = block.find_element(By.CSS_SELECTOR, "em")
#
#         #element = driver.find_element_by_id('id_of_your_element')
#         driver.execute_script("arguments[0].click();", click_more)
#
#         #wait = WebDriverWait(driver, 10)
#         #click_more = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "em")))
#
#         #click_more.click()
#         print('Click!')
#
#         time.sleep(3)
#
#         messages = block.find_elements(By.CSS_SELECTOR, "div[id]")
#
#         for massage in messages:
#             if 'plus' in massage.get_attribute('id'):
#                 plus = massage.text.replace('<<Скрыть', '')
#
#             if 'minus' in massage.get_attribute('id'):
#                 minus = massage.text.replace('<<Скрыть', '')
#
#         print(plus)
#         print(minus)
#
#         await generator(url_answer, author, formatted_date, plus, minus)
#
#     time.sleep(5)


async def check_ocompanii(service):
    url = 'https://ocompanii.net/company/information.php?cid=764047'

    links = await pars_url()

    print(cor_path)
    print(abspath)

    # chrome_options = Options()
    # #chrome_options.add_argument(fr"user-data-dir={cor_path}/Skillbox")
    # chrome_options.add_argument("--headless")
    # driver = webdriver.Chrome(options=chrome_options)

    display = Display(visible=0, size=(800, 600))
    display.start()

    # now Firefox will run in a virtual display.
    # you will not see the browser.
    # gecko_path = f"{abspath}/geckodriver"  # Замените на фактический путь к geckodriver
    # service = Service(gecko_path)
    # driver = webdriver.Firefox(service=service)

    chrome_options = Options()
    chrome_options.add_argument("--user-data-dir=wb")
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

        await generator(service, url_answer, author, formatted_date, plus, minus)

    time.sleep(5)



if __name__ == '__main__':
    service = asyncio.run(get_service())

    asyncio.run(check_ocompanii(service))
    data = {'service_name': 'OCOMPANII', 'date': time.ctime()}
    asyncio.run(skillbox_sheet(service, '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8', 'logs', data))