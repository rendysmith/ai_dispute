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

async def extract_ids(url):
    pattern = r'id=(\d+)&comment'
    ids = re.search(pattern, url).group(1)
    return ids

async def check_ocompanii(service):
    links = await pars_url(service)
    #links = []

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'http://example.com',
        'Upgrade-Insecure-Requests': '1'
    }

    url = 'https://ocompanii.net/company/information.php?cid=764047'
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    #print(soup)

    blocks = soup.find_all('div', class_='col-sm-12 col-md-12')
    #print(len(blocks))

    add_comments = soup.find_all('a', class_='btn-primary3')
    #print(len(add_comments))

    for add_com in add_comments:
        print('================================================')
        url_comm = add_com.get('href')
        id_ = await extract_ids(url_comm)
        #print(id_)

        url_answer = f'https://ocompanii.net/reviews/detail.php?id={id_}'
        url_full_comm = f'https://ocompanii.net/reviews/load_detail.php?id={id_}'

        if url_answer in links:
            print(f'{url_answer}\nНа этот отзыв уже есть реакция!\n')
            continue

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        author = soup.find('span', {'itemprop': 'author'}).text
        print(author)

        blocks = soup.find_all('div', class_='col-sm-12 col-md-12')
        for block in blocks:
            formatted_date = 'No Date'
            spans = block.find_all("span")
            #print(len(spans))
            if len(spans) == 0:
                continue

            brk = False

            for span in spans:
                span_text = span.text.strip()
                #print(f'span.text {span_text}')
                try:
                    date = datetime.strptime(span_text, "%Y-%m-%d %H:%M:%S")
                    print("date", date)

                except Exception as Ex:
                    #print('ERROR Ex', Ex)
                    continue

                #unix_time = date.timestamp()
                if (current_date - date) > timedelta(days=30):
                    print(f'--- Отзыв старше 30 дней. = {date}\n')
                    brk = True
                    break

                else:
                    print(f'+++ Отзыв в пределах 30 дней = {date}\n'
                          f'{current_date - date} > {timedelta(days=30)}')
                    formatted_date = date.strftime("%d.%m.%Y")
                    brk = True
                    break

            if brk:
                break

        print(formatted_date)

        response = requests.get(url_full_comm, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser').text
        print(type(soup))
        print(soup)

        p_m = soup.split('###')
        plus = p_m[-2]
        minus = p_m[-1]

        await generator(service, url_answer, author, formatted_date, plus, minus)


async def check_ocompanii_old(service):
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
    #print(len(hrefs))

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