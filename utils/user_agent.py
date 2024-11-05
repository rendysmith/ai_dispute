import json
import traceback
import zipfile

from playwright.async_api import async_playwright

import asyncio
import aiohttp
from aiohttp_proxy import ProxyConnector, ProxyType

import requests
from bs4 import BeautifulSoup
import cloudscraper
import re

from fake_useragent import UserAgent


from selenium import webdriver
#from selenium_authenticated_proxy import SeleniumAuthenticatedProxy
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from utils.proxy_bridge import get_iplist, get_one_proxy
import os
from dotenv import load_dotenv

from utils.constants import status_codes

from seleniumbase import Driver
from seleniumbase import config
config.DISABLE_COLORS = True


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

async def get_soup_anticloud(url):
    scraper = cloudscraper.create_scraper(
        browser={
            "browser": "chrome",
            "platform": "windows",
        },
    )

    # Установка прокси с авторизацией
    response = scraper.get(url, timeout=15000)
    status_code_1 = response.status_code
    print(f"Anti CF Proxy {status_code_1}:", status_code_1)

    if status_code_1 == 507:
        print(f'{status_code_1}: {status_codes.get(status_code_1)}')

    if status_code_1 == 521:
        print(f'{status_code_1}: {status_codes.get(status_code_1)}')

    if status_code_1 != 200:
        proxy_host, proxy_port = await get_one_proxy()
        scraper.proxies = {
            "http": f"http://{login_proxy}:{pass_proxy}@{proxy_host}:{proxy_port}",
            "https": f"http://{login_proxy}:{pass_proxy}@{proxy_host}:{proxy_port}",
        }

        #print(scraper.proxies)
        response = scraper.get(url, timeout=15000)
        status_code_2 = response.status_code
        print(f"Anti CF No proxy {status_code_2}:", status_code_2)

        if status_code_2 == 507:
            print(f'{status_code_2}: {status_codes.get(status_code_2)}')

        if status_code_2 == 521:
            print(f'{status_code_2}: {status_codes.get(status_code_2)}')

        if status_code_2 != 200:
            return None

    soup = BeautifulSoup(response.text, "html.parser")
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

async def get_selenium(url=None, headless=True):
    print('- >>> Selenium No Proxy...')
    chrome_options = Options()
    if headless == True:
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

    # Инициализация драйвера
    driver = webdriver.Chrome(options=chrome_options)
    #driver.get(url)

    # Ожидание загрузки определенного элемента (например, заголовка)
    #wait = WebDriverWait(driver, 10)
    print('- <<< Selenium No Proxy connect')
    return driver

async def get_selenium_proxy(url=None, headless=True, proxy=True):
    if proxy:
        print('>>> Selenium proxy...')
        proxy_host, proxy_port = await get_one_proxy()
        print(f'Proxy: {proxy_host}:{proxy_port}')
        proxy = f"{login_proxy}:{pass_proxy}@{proxy_host}:{proxy_port}"

        # create a Driver instance with undetected_chromedriver (uc) and headless mode
        driver = Driver(uc=True,
                        headless=headless,
                        headless1=headless,
                        headless2=headless,
                        proxy=proxy,
                        agent=ua.chrome,
                        log_cdp_events=True
                        )
        #driver.get(url)
        print('<<< Selenium connect')
        return driver

    else:
        print('>>> Selenium NO proxy...')
        # create a Driver instance with undetected_chromedriver (uc) and headless mode
        driver = Driver(uc=True,
                        headless=headless,
                        headless1=headless,
                        headless2=headless,
                        agent=ua.chrome,
                        log_cdp_events=True
                        )
        #driver.get(url)
        print('<<< Selenium connect')
        return driver

async def get_playwright(url, headless=True):
    print('>>> start PW')
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


            json_file = os.path.join(os.path.dirname(__file__), 'setting/context.json')

            try:
                context = await browser.new_context(user_agent=ua.firefox, storage_state=json.load(open(json_file)))
            except:
                context = await browser.new_context(user_agent=ua.firefox)

            await context.set_extra_http_headers(await gen_ua(url))
            page = await context.new_page()

            # Перехватываем запросы для блокировки изображений и видео
            async def block_images_and_videos(route):
                if route.request.resource_type in ["image", "media"]:
                    await route.abort()
                else:
                    await route.continue_()

            #await page.route("**/*", block_images_and_videos)
            await page.goto(url)
            # Сохранение контекста в файл
            context_state = await context.storage_state()
            with open(json_file, 'w') as f:
                json.dump(context_state, f)

            return browser, page

        try:
            # Если ошибка, запускаем c прокси
            proxies = await get_headers('pw')
            browser, page = await launch_browser(proxies)
            print('Proxy')

        except:
            # Пытаемся запустить без прокси
            browser, page = await launch_browser()
            print('No Proxy')

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
    #soup = await get_soup_anticloud(url)
    #soup = await get_soup(url, only_text=False)

    #playwright, browser, page = await get_playwright(url, headless=False)

    driver = await get_selenium_proxy(url, headless=False)





if "__main__" in __name__:
    #asyncio.run(get_playwright('https://yandex.ru/maps/org/149979773456/reviews', headless=False))
    #asyncio.run(tst_proxy())
    url = 'https://ocompanii.net/reviews/detail.php?id=1137222'
    url = "https://httpbin.org/ip"
    url = 'https://irecommend.ru/content/2-nedeli-polet-normalnyi'
    url = 'https://otzovik.com/reviews/molochnaya_smes_nutrilon_gipoallergenniy/?order=date_desc'

    asyncio.run(main(url))
    # url = 'https://yandex.ru/maps/2/saint-petersburg/geo/zhiloy_kompleks_biografiya/4184971603/?ll=30.281608%2C59.960850&z=15.46'
    # playwright, browser, page = asyncio.run(get_playwright(url))
    # if page:
    #     print(page.url)
    #     print('OK!')


    #
    #
    # def enable_secure_dns(driver):
    #     # Включаем Secure DNS и выбираем Cloudflare (1.1.1.1)
    #     driver.execute_cdp_cmd("Network.setExtraHTTPHeaders", {
    #         "headers": {
    #             "Secure-DNS": "1.1.1.1"
    #         }
    #     })
    #
    # chrome_options = webdriver.ChromeOptions()
    # chrome_options.add_argument(f'--user-agent={ua.chrome}')
    # chrome_options.add_argument("--no-sandbox")
    # chrome_options.add_argument("--disable-dev-shm-usage")
    #
    # # Initialize SeleniumAuthenticatedProxy
    # proxy_helper = SeleniumAuthenticatedProxy(proxy_url=f"http://{proxy}")
    #
    # # Enrich Chrome options with proxy authentication
    # proxy_helper.enrich_chrome_options(chrome_options)
    #
    # # Start WebDriver with enriched options
    # driver = webdriver.Chrome(options=chrome_options)
    # enable_secure_dns(driver)
    # driver.get(url)
    #
    # return driver


    # from seleniumwire.undetected_chromedriver import Chrome
    #
    # chrome_options = Options()
    # if headless == True:
    #     chrome_options.add_argument("--headless")
    #     chrome_options.add_argument("--no-sandbox")
    #     chrome_options.add_argument("--disable-dev-shm-usage")
    #
    # chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    #
    #
    #
    # seleniumwire_options = {
    #     'proxy': {
    #         'http': f'http://{login_proxy}:{pass_proxy}@{proxy_host}:{proxy_port}',
    #         'verify_ssl': False,
    #     },
    # }
    #
    # # driver = webdriver.Chrome(
    # #     seleniumwire_options=seleniumwire_options
    # # )
    # driver = Chrome(options=chrome_options, seleniumwire_options=seleniumwire_options)
    # driver.get(url)
    #
    # # Ожидание загрузки определенного элемента (например, заголовка)
    # wait = WebDriverWait(driver, 10)
    # return driver
