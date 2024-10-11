import traceback

from playwright.async_api import async_playwright

import asyncio
import aiohttp
from aiohttp_proxy import ProxyConnector, ProxyType

import requests
from bs4 import BeautifulSoup
import re

from fake_useragent import UserAgent
from sqlalchemy.util import await_only

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

async def get_soup(url, only_text=True):
    if only_text: #Получить только текст
        r_text = await get_data_without_proxy(url)
        if not r_text:
            r_text = await get_data_with_proxy(url)
            print('Soup Proxy!')

            if not r_text:
                return None

        soup = await get_soup_bs4(r_text, only_pars=True)
        return soup

    else: #Получить json()
        r_json = await get_data_without_proxy(url, text_format=False)
        if not r_json:
            r_json = await get_data_with_proxy(url, text_format=False)

        return r_json





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

async def get_playwright(url, headless=True):
    """
     :param url: url
     :param headless: headless (boot) headless=True
     :return:
     """
    try:
        playwright = await async_playwright().start()

        async def launch_browser(proxy=None):
            """Запуск браузера с опциональным прокси и настройкой контекста"""
            browser = await playwright.firefox.launch(
                headless=headless,
                proxy=proxy,
                timeout=15000 if proxy else 30000
            )
            context = await browser.new_context(user_agent=ua.random)
            page = await context.new_page()

            # Перехватываем запросы для блокировки изображений и видео
            async def block_images_and_videos(route):
                if route.request.resource_type in ["image", "media"]:
                    await route.abort()
                else:
                    await route.continue_()

            await page.route("**/*", block_images_and_videos)
            await page.goto(url)
            return browser, page

        # Пытаемся запустить с прокси
        try:
            # Если ошибка, запускаем без прокси
            browser, page = await launch_browser()
            print('No Proxy')

        except:
            proxies = await get_headers('pw')
            browser, page = await launch_browser(proxies)
            print('Proxy')

        return playwright, browser, page

    except Exception as Ex:
        print("ERROR PW Ex:", Ex)
        traceback.print_exc()
        return None, None, None

async def get_data_with_proxy(url, text_format=True):
    for i in range(2):
        print(f'Proxy {i}')
        proxy_host, proxy_port = await get_one_proxy()
        connector = ProxyConnector(proxy_type=ProxyType.HTTP,
                                   host=proxy_host,
                                   port=proxy_port,
                                   username=login_proxy,
                                   password=pass_proxy)

        timeout = aiohttp.ClientTimeout(total=10)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            print('--1--')
            try:
                async with session.get(url) as response:
                    print('--2--')
                    status_code = response.status
                    print("Status:", status_code)

                    if status_code == 403:
                        return None

                    elif status_code == 507:
                        return None

                    response.raise_for_status()
                    if text_format:
                        return await response.text()
                    else:
                        return await response.json()

            except asyncio.TimeoutError as TE:
                print(f"Error Proxy TE: {TE}")
                await asyncio.sleep(5)  # Ждем перед повторной попыткой

            except Exception as Ex:
                print(f"{i} Error Proxy Ex: {Ex}")
                await asyncio.sleep(5)
    return None

async def get_data_without_proxy(url, text_format=True):
    for i in range(2):
        print(f'Proxy {i}')

        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            print('--1--')
            try:
                async with session.get(url) as response:
                    print('--2--')
                    status_code = response.status
                    print("Status:", status_code)

                    if status_code == 403:
                        return None

                    elif status_code == 507:
                        return None

                    response.raise_for_status()
                    if text_format:
                        return await response.text()
                    else:
                        return await response.json()

            except asyncio.TimeoutError as TE:
                print(f"Error Proxy TE: {TE}")
                await asyncio.sleep(5)  # Ждем перед повторной попыткой

            except Exception as Ex:
                print(f"{i} Error Proxy Ex: {Ex}")
                await asyncio.sleep(5)
    return None

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

async def main(url):
    soup = await get_soup(url, only_text=False)
    print(soup)



if "__main__" in __name__:
    #asyncio.run(get_playwright('https://yandex.ru/maps/org/149979773456/reviews', headless=False))
    #asyncio.run(tst_proxy())
    url = 'https://ocompanii.net/reviews/detail.php?id=1137222'
    url = "https://httpbin.org/ip"

    asyncio.run(main(url))
    # url = 'https://yandex.ru/maps/2/saint-petersburg/geo/zhiloy_kompleks_biografiya/4184971603/?ll=30.281608%2C59.960850&z=15.46'
    # playwright, browser, page = asyncio.run(get_playwright(url))
    # if page:
    #     print(page.url)
    #     print('OK!')
