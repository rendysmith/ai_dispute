import asyncio
import json
import os

import aiohttp
from cloudscraper import session
from dotenv import load_dotenv

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from utils.user_agent import get_selenium

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

username = os.environ.get("LOGIN_DA")
password = os.environ.get("PASS_DA")

async def get_cookies():
    url = 'https://brandanalytics.ru/account/login_check'

    

    async with aiohttp.ClientSession() as session:
        async with session.post(url)


async def get_json(driver):
    base_url = "https://brandanalytics.ru/theme-data/12551940/"
    params = "?tst=1723496399&tsf=1723237200&requested[]=feed&sort=time_create&order=desc&page=2&limit=25&filter[ft][not][]=30008&filter[ft][not][]=30009&filter[ft][not][]=15&filter[ft][not][]=30059&filter[ft][not][]=30025&filter[fmsgproc][any][]=1"
    url = base_url + params

    driver.get(url)
    json_text = driver.find_element(By.TAG_NAME, "body").text

    # Парсим текст как JSON
    json_data = json.loads(json_text)

    # Выводим полученные данные
    print(type(json_data))
    print(json_data)



async def check_brandanalytics(url):

    driver = await get_selenium(url, headless=False)

    login_input = driver.find_element(By.CSS_SELECTOR, 'input[class="login-form__input"][name="_username"]')
    login_input.send_keys(username)

    pass_input = driver.find_element(By.CSS_SELECTOR, 'input[class="login-form__input"][name="_password"]')
    pass_input.send_keys(password)

    pass_input.send_keys(Keys.ENTER)

    driver.get(url)
    await get_json(driver)

    len_span = 0
    while len_span == 0:
        pages = driver.find_elements(By.CSS_SELECTOR, 'span[class="page_item"]')
        len_span = len(pages)
        print(f'Wait 3 sec...({len_span})')
        await asyncio.sleep(3)

    for page in pages:
        pages = int(page.text)

    wait = WebDriverWait(driver, 10)
    #print(driver.page_source)
    await get_json(driver)
    for i in range(pages):

        len_blocks = 0
        while len_blocks == 0:
            blocks = driver.find_elements(By.CSS_SELECTOR, 'div[class="feed_item feed_item__small"]')
            len_blocks = len(blocks)
            print(f"Wait 3 sec.({len_blocks})")
            await asyncio.sleep(3)

        for block in blocks:
            date = block.find_element(By.CSS_SELECTOR, 'div[class="msg_date info_item"]').text
            print(date)

            feedback = block.find_element(By.CSS_SELECTOR, '')



        new_url = f"{url[:-1]}{i+2}"
        driver.get(new_url)
        wait = WebDriverWait(driver, 10)






    # url = "https://brandanalytics.ru/theme-data/12551940/"
    # async with aiohttp.ClientSession() as session:
    #     async with session.get(url, auth=aiohttp.BasicAuth(username, password)) as response:
    #         text = await response.json()
    #         print(text)


async def main(url):
    await check_brandanalytics(url)


if "__main__" in __name__:
    url = "https://brandanalytics.ru/report/12551940/summary?tsf=1723237200&tst=1723496399&ft%5Bnot%5D=30008&ft%5Bnot%5D=30009&ft%5Bnot%5D=15&ft%5Bnot%5D=30059&ft%5Bnot%5D=30025&fmsgproc%5Bany%5D=1&page=1"
    #url = "https://brandanalytics.ru/report/12551940/summary?tsf=1723237200&tst=1723496399&fmsgproc[any]=1&page=1"

    asyncio.run(main(url))
