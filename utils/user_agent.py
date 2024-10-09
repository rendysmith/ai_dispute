from playwright.async_api import async_playwright

import asyncio
import aiohttp
from aiohttp_proxy import ProxyConnector, ProxyType

import requests
from bs4 import BeautifulSoup
import re

from fake_useragent import UserAgent

from utils.proxy_bridge import get_iplist, get_one_proxy
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
    host, port = await get_one_proxy()
    #port = '8080'
    print(host, port)

    if not host:
        return None

    if module == 'soup':
        proxies = {
            'http': f'http://{login_proxy}:{pass_proxy}@{host}:{port}',
            'https': f'https://{login_proxy}:{pass_proxy}@{host}:{port}'
        }

    elif module == 'pw':
        proxies = {
            "server": f"{host}:{port}",
            "username": login_proxy,  # Опционально, если прокси требует аутентификации
            "password": pass_proxy  # Опционально, если прокси требует аутентификации
        }

    return proxies


async def get_soup_bs4(url, only_pars=False):
    if only_pars == False:
        domen = await extract_main_site(url)
        headers = await gen_ua(domen)
        timeout = 30000

        response = requests.get(url, headers=headers, timeout=timeout)
        status_code = response.status_code
        print(f'Status code = {status_code}')
        if status_code == 200:
            response_text = response.text

        elif status_code == 403:
            print('403 - необходима регистрация.')
            return None

        else:
            try:
                response_text = await get_data_with_proxy(url)
                if not response_text:
                    return None

            except Exception as Ex:
                print(f'Proxy Ex: {Ex}')
                return None

        soup = BeautifulSoup(response_text, 'html.parser')

    else:
        soup = BeautifulSoup(url, 'html.parser')

    return soup

async def get_soup(url):
    r_text = await get_data_with_proxy(url)
    if r_text:
        soup = await get_soup_bs4(r_text, only_pars=True)

    else:
        soup = await get_soup_bs4(url)
    return soup

async def get_soup_new(url, only_pars=False):
    if not only_pars:
        domen = await extract_main_site(url)
        headers = await gen_ua(domen)
        proxies = await get_headers('soup')
        timeout = aiohttp.ClientTimeout(total=60)  # Устанавливаем таймаут в 30 секунд

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, proxy=proxies['https'], timeout=timeout) as response:
                status_code = response.status
                print(status_code)

                if status_code == 200:
                    response_text = await response.text()
                    print(response_text)

        soup = BeautifulSoup(response_text, 'html.parser')

    else:
        soup = BeautifulSoup(url, 'html.parser')

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

async def get_playwright(url, headless=True, proxy=True):
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

async def get_data_with_proxy(url):
    for i in range(5):
        proxy_host, proxy_port = await get_one_proxy()
        connector = ProxyConnector(proxy_type=ProxyType.HTTP,
                                   host=proxy_host,
                                   port=proxy_port,
                                   username=login_proxy,
                                   password=pass_proxy)

        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(url) as response:
                try:
                    status_code = response.status
                    print("Status:", status_code)

                    if status_code == 403:
                        return None

                    elif status_code == 507:
                        return None

                    response.raise_for_status()
                    return await response.text()

                except Exception as Ex:
                    print(f"{i} Error Proxy Ex: {Ex}")
                    await asyncio.sleep(5)

async def main():
    url = 'https://irecommend.ru/content/ustraivaet-vo-vsekh-usloviyakh-ekspluatatsii'
    driver = await get_playwright(url)
    input('Wait')

    top_block = driver.find_element(By.CSS_SELECTOR, 'h1[class="largeHeader"]')
    if top_block:
        print(1)
    else:
        print(2)

async def tst_proxy():
    print('-----------------')
    url = 'https://ifconfig.me/all.json'
    response = await get_data_with_proxy(url)
    print(response)

    soup = await get_soup(url)
    print(soup)

    print('---------2--------')
    url = 'https://api.ipify.org?format=json'
    soup = await get_soup(url)
    print(soup)




if "__main__" in __name__:
    #asyncio.run(get_playwright('https://yandex.ru/maps/org/149979773456/reviews', headless=False))
    #asyncio.run(tst_proxy())
    url = 'https://ocompanii.net/reviews/detail.php?id=1137222'
    #url = "https://httpbin.org/ip"
    asyncio.run(get_data_with_proxy(url))
