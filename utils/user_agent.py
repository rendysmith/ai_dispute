import urllib3.exceptions

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
        'User-Agent': ua.random,
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': url}

    return headers

async def get_headers(module):
    host_port = await get_iplist()
    if not host_port:
        return None

    if module == 'soup':
        proxies = {
            'http': f'http://{login_proxy}:{pass_proxy}@{host_port}',
            'https': f'https://{login_proxy}:{pass_proxy}@{host_port}'
        }

    elif module == 'pw':
        proxies = {
            "server": "host_port",
            "username": login_proxy,  # Опционально, если прокси требует аутентификации
            "password": pass_proxy  # Опционально, если прокси требует аутентификации
        }

    return proxies


async def get_soup(url, only_pars=False):

    if only_pars == False:
        domen = await extract_main_site(url)
        headers = await gen_ua(domen)
        timeout = 30000

        try:
            print('No proxy!')
            response = requests.get(url, headers=headers, timeout=timeout)

        except requests.exceptions.ConnectTimeout as CT:
            try:
                print(f'Error CT: {CT}')
                proxies = await get_headers('soup')
                response = requests.get(url, headers=headers, proxies=proxies, timeout=timeout)

            except:
                return None

        except requests.exceptions.ProxyError as PE:
            try:
                print(f'Error PE: {PE}')
                proxies = await get_headers('soup')
                response = requests.get(url, headers=headers, proxies=proxies, timeout=timeout)
            except:
                return None

        except requests.exceptions.Timeout as To:
            try:
                print(f'Error To: {To}')
                proxies = await get_headers('soup')
                response = requests.get(url, headers=headers, proxies=proxies, timeout=timeout)
            except:
                return None

        except urllib3.exceptions.ConnectTimeoutError as CTE:
            try:
                print(f'Error CTE: {CTE}')
                proxies = await get_headers('soup')
                response = requests.get(url, headers=headers, proxies=proxies, timeout=timeout)
            except:
                return None

        except urllib3.exceptions.MaxRetryError as MRE:
            try:
                print(f'Error MRE: {MRE}')
                proxies = await get_headers('soup')
                response = requests.get(url, headers=headers, proxies=proxies, timeout=timeout)
            except:
                return None

        except requests.exceptions.RequestException as RE:
            try:
                print(f'Error RE: {RE}')
                proxies = await get_headers('soup')
                response = requests.get(url, headers=headers, proxies=proxies, timeout=timeout)
            except:
                return None

        if response.status_code != 200:
            print(response.status_code)
            proxies = await get_headers('soup')
            response = requests.get(url, headers=headers, proxies=proxies, timeout=timeout)

            if response.status_code != 200:
                return None

        soup = BeautifulSoup(response.text, 'html.parser')

    else:
        soup = BeautifulSoup(url, 'html.parser')

    print(soup)
    return soup

async def get_selenium(url, headless=True):
    chrome_options = Options()
    if headless == True:
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

    # Инициализация драйвера
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)

    # Ожидание загрузки определенного элемента (например, заголовка)
    wait = WebDriverWait(driver, 10)
    return driver

async def get_playwright(url, headless=True, proxy=False):
    """
    :param url: url
    :param headless: headless (boot) headless=True
    :return:
    """

    try:
        playwright = await async_playwright().start()
        if proxy:
            proxies = await get_headers('pw')
            browser = await playwright.firefox.launch(
                headless=headless,
                proxy=proxies,  # Прокси передаётся здесь
                timeout=30000)

        else:
            browser = await playwright.firefox.launch(headless=headless, timeout=30000)

        context = await browser.new_context(
            user_agent=ua.random)
        page = await context.new_page()

        # ---------------------------------------------------------
        # Перехватываем запросы для блокировки изображений и видео
        async def block_images_and_videos(route):
            if route.request.resource_type in ["image", "media"]:
                await route.abort()  # Отклоняем запросы на изображения и видео
            else:
                await route.continue_()  # Разрешаем все остальные запросы

        # Применяем фильтр на все запросы
        await page.route("**/*", block_images_and_videos)
        #---------------------------------------------------------
        await page.goto(url)
        return playwright, browser, page

    except Exception as Ex:
        print("ERROR PW Ex:", Ex)
        return None, None, None

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
    #asyncio.run(get_playwright('https://vk.com/wall-7871245_252922?reply=253324&thread=252946', headless=False))
    asyncio.run(get_soup('https://mail.ru'))