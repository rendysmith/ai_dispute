from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright

import asyncio
import requests
from bs4 import BeautifulSoup
import re

from fake_useragent import UserAgent

from utils.proxy_bridge import get_iplist
import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

login_proxy = os.environ.get("LOGIN_PROXY")
pass_proxy = os.environ.get("PASS_PROXY")

ua = UserAgent()

async def extract_main_site(url):
    match = re.match(r'(https?://[^/]+)', url)
    return match.group(0) if match else None

async def gen_ua(url):
    headers = {
        'User-Agent': ua.chrome,
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': url}

    return headers

async def get_soup(url):
    domen = await extract_main_site(url)
    headers = await gen_ua(domen)

    try:
        print('No proxy!')
        response = requests.get(url, headers=headers)

    except requests.exceptions.ProxyError as PE:
        print('With proxy!')
        host_port = await get_iplist()
        proxies = {
            'http': f'http://{login_proxy}:{pass_proxy}@{host_port}',
            'https': f'https://{login_proxy}:{pass_proxy}@{host_port}'
        }
        response = requests.get(url, headers=headers, proxies=proxies)

    soup = BeautifulSoup(response.text, 'html.parser')
    return soup

async def get_selenium(url):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Инициализация драйвера
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)

    # Ожидание загрузки определенного элемента (например, заголовка)
    wait = WebDriverWait(driver, 10)

    return driver

async def get_playwright(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # Launch browser
        page = await browser.new_page()

        await page.goto(url)

        return page

        # top_block = await page.query_selector('h1[class="largeHeader"]')
        # print(top_block)
        #
        # top_block = page.locator('div.headerWithMenu_margin30')
        # top_link = top_block.locator('a')
        #
        # # Получаем href атрибут ссылки
        # href = await top_link.get_attribute('href')
        # print(href)
        #
        # # Формируем полный URL
        # top_url = domen + href + "?new=1"
        # print(top_url)
        #
        # await browser.close()

async def main():
    url = 'https://irecommend.ru/content/ustraivaet-vo-vsekh-usloviyakh-ekspluatatsii'
    driver = await get_playwright(url)
    input('Wait')

    top_block = driver.find_element(By.CSS_SELECTOR, 'h1[class="largeHeader"]')
    if top_block:
        print(1)
    else:
        print(2)


if "__main__" in __name__:
    asyncio.run(main())