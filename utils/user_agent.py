import json
import traceback

import asyncio
import aiohttp
from aiohttp_proxy import ProxyConnector, ProxyType

import requests
from bs4 import BeautifulSoup
import cloudscraper
import re

from fake_useragent import UserAgent

import os
from dotenv import load_dotenv

from utils.constants import status_codes
from utils.proxy_module import get_one_proxy

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from webdriver_manager.chrome import ChromeDriverManager

from seleniumbase import Driver
from seleniumbase import config
from seleniumbase import SB

os.environ['DISABLE_COLIED_TRACEBACK'] = '1'
os.environ["DISABLE_COLORAMA"] = "1"
os.environ["SELENIUMBASE_COLOR"] = "0"

config.DISABLE_COLORS = True

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

# login_proxy = os.environ.get("LOGIN_PROXY")
# pass_proxy = os.environ.get("PASS_PROXY")

ua = UserAgent()

async def clean_html(raw: str) -> str:
    import html
    # убираем теги
    text = BeautifulSoup(raw, "html.parser").get_text(separator="\n")
    # декодируем символы
    return html.unescape(text).strip()

async def get_soup_tor(url, error=False):
    from aiohttp import ClientSession
    from aiohttp_socks import ProxyConnector
    from stem.control import Controller
    from stem import Signal

    TOR_PROXY = "socks5://127.0.0.1:9050"
    TOR_PORT = 9051  # ControlPort
    TOR_PASSWORD = "mypassword"  # твой пароль (а не hash!)

    if error:
        print('--- Change tor IP')
        with Controller.from_port(port=TOR_PORT) as controller:
            controller.authenticate(password=TOR_PASSWORD)
            controller.signal(Signal.NEWNYM)

    print('--- Start get data tor')
    connector = ProxyConnector.from_url(TOR_PROXY)
    async with ClientSession(connector=connector) as session:
        async with session.get(url, timeout=60) as resp:
            html = await resp.text()
            print('--- Return data')
            return BeautifulSoup(html, "html.parser")

async def get_fetcher_local(api_url, flare_bypasser_url="http://localhost:8080/v1"):
    """
    Fetches JSON data from a sravni.ru API endpoint using FlareBypasser.

    Args:
        api_url: The URL of the sravni.ru API endpoint.
        flare_bypasser_url: The URL of your running FlareBypasser instance.

    Returns:
        A Python dictionary containing the JSON data, or None if there's an error.
    """

    headers = {"Content-Type": "application/json"}
    data = {
        "cmd": "request.get",  # or "request.get_cookies" depending on API needs
        "url": api_url,
        "maxTimeout": 60000  # Adjust timeout as needed
    }

    try:
        response = requests.post(flare_bypasser_url, headers=headers, json=data)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        json_response = response.json()

        if json_response["status"] == "ok":
            #  Handle different response structures based on FlareBypasser's output.
            # This example assumes a "response" field containing the JSON data.  Adjust as needed!

            if "response" in json_response["solution"]:
              return json.loads(json_response["solution"]["response"])
            elif "cookies" in json_response["solution"]:
              #If cookies are returned, you need to make a second request using those cookies.
              cookies = {cookie['name']: cookie['value'] for cookie in json_response['solution']['cookies']}
              second_request = requests.get(api_url, cookies=cookies)
              second_request.raise_for_status()
              return second_request.json()
            else:
              print("Unexpected response format from FlareBypasser.")
              return None

        else:
            print(f"Error from FlareBypasser: {json_response.get('message', 'Unknown error')}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"GFL An error occurred: {e}")
        return None

async def get_soup_curl_cffi(url, dict_type=True, proxy=True):
    from curl_cffi import requests

    # Настройки для имитации браузера
    headers = {
        'User-Agent': ua.chrome,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    # Конфигурация прокси
    proxy_config = None
    if proxy:
        host, port = await get_one_proxy()
        proxy = f'http://{login_proxy}:{pass_proxy}@{host}:{port}'

        proxy_config = {
            'url': proxy,  # формат: 'http://user:pass@host:port' или 'http://host:port'
            'verify': False  # отключение проверки сертификата для прокси
        }

    try:
        # Выполнение запроса с обходом Cloudflare и прокси
        response = requests.get(
            url,
            headers=headers,
            impersonate="chrome124",  # Обновленная версия Chrome 119
            proxies=proxy_config,  # Использование прокси
            verify=True,  # Проверка SSL-сертификата
            timeout=30  # Таймаут подключения
        )

        # Проверка успешности запроса
        if response.status_code == 200:
            # Парсинг содержимого (пример с BeautifulSoup)

            if dict_type:
                return response.json()

            else:
                soup = BeautifulSoup(response.text, 'html.parser')
                return soup

        else:
            print(f"Ошибка curl_cffi: {response.status_code}")
            return None

    except Exception as e:
        print(f"Произошла ошибка при парсинге curl_cffi: {e}")
        return None

async def extract_main_site(url):
    match = re.match(r'(https?://[^/]+)', url)
    return match.group(0) if match else None

async def gen_ua(url):
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        "Content-Type": "application/json",
        'User-Agent': ua.random,
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
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

async def get_soup(url, only_text=True, proxy=True):
    '''
    only_text = True - получить данные в SOUP формате
    only_text = False - в формате JSON
    '''

    if only_text: #Получить только текст
        if proxy:
            r_text = await get_data_with_proxy(url)
            print('Soup Proxy!')

            if not r_text:
                return None

        else:
            r_text = await get_data_without_proxy(url)
            if not r_text:
                return None

        soup = await get_soup_bs4(r_text, only_pars=True)
        return soup

    else: #Получить json()
        if proxy:
            r_json = await get_data_with_proxy(url, text_format=False)
        else:
            r_json = await get_data_without_proxy(url, text_format=False)
        return r_json

async def get_soup_anticloud(url, only_json=True, proxy=True):
    headers = {'User-Agent': ua.chrome}

    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True,
            'mobile': False,
        }
    )

    if proxy:
        proxy_host, proxy_port = await get_one_proxy()
        scraper.proxies = {
            "http": f"http://{login_proxy}:{pass_proxy}@{proxy_host}:{proxy_port}",
            "https": f"http://{login_proxy}:{pass_proxy}@{proxy_host}:{proxy_port}",
        }

    # Установка прокси с авторизацией
    response = scraper.get(url, headers=headers, timeout=15000)
    status_code_1 = response.status_code
    print(f"Anti CF Proxy {status_code_1}:", status_code_1)

    if status_code_1 != 200:
        print(f'{status_code_1}: {status_codes.get(status_code_1, None)}')
        return None

    if only_json:
        return response.json()

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

async def get_selenium(url=False, headless=True, profile=False, proxy=False):
    chrome_options = Options()
    if proxy:
        print('- >>> Selenium WITH Proxy...')
        proxy_host, proxy_port = await get_one_proxy()
        print(proxy_host)
        chrome_options.add_argument(f'--proxy-server={login_proxy}:{pass_proxy}@{proxy_host}:{proxy_port}')

    else:
        print('- >>> Selenium WITHOUT Proxy...')

    if headless:
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--remote-debugging-port=9222")

        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-web-security')

    if profile:
        chrome_options.add_argument(f"--user-data-dir={profile}")

    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

    # Инициализация драйвера
    driver = webdriver.Chrome(options=chrome_options)

    if url:
        driver.get(url)

    # Ожидание загрузки определенного элемента (например, заголовка)
    #wait = WebDriverWait(driver, 10)
    print('- <<< Selenium No Proxy connect')
    return driver

async def get_selenium_anticloud(url=None, headless=False, proxy=True):
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-extensions")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")

    options.headless = headless

    #service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(options=options)

    # Дополнительно можно модифицировать User-Agent
    driver.execute_cdp_cmd("Network.setUserAgentOverride", {
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    driver.get(url)
    await asyncio.sleep(5)

    try:
        # Поиск всех iframe на странице
        iframes = driver.find_elements(By.TAG_NAME, "iframe")

        # Если iframe найдены, перебираем их
        if iframes:
            for iframe in iframes:
                try:
                    driver.switch_to.frame(iframe)

                    # Попытка 1: стандартный чекбокс
                    try:
                        checkbox = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='checkbox']"))
                        )
                        human_like_click(checkbox, driver)
                        print("Нашли чекбокс через input[type='checkbox']")
                        return True
                    except:
                        pass

                    # Попытка 2: чекбокс Cloudflare внутри label
                    try:
                        checkbox = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "label.check"))
                        )
                        human_like_click(checkbox, driver)
                        print("Нашли чекбокс через label.check")
                        return True
                    except:
                        pass

                    # Попытка 3: чекбокс как div
                    try:
                        checkbox = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "div.checkbox"))
                        )
                        human_like_click(checkbox, driver)
                        print("Нашли чекбокс через div.checkbox")
                        return True
                    except:
                        pass

                    # Попытка 4: по XPath, ищем элемент рядом с текстом "Verify you are human"
                    try:
                        checkbox = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable(
                                (By.XPATH, "//*[contains(text(), 'Verify you are human')]/preceding::input[1]"))
                        )
                        human_like_click(checkbox, driver)
                        print("Нашли чекбокс через XPath около текста")
                        return True
                    except:
                        pass

                    # Возвращаемся из iframe если не нашли чекбокс
                    driver.switch_to.default_content()
                except:
                    # Если произошла ошибка при переключении на iframe, возвращаемся к основному контенту
                    driver.switch_to.default_content()

        # Если в iframe не нашли, попробуем найти на основной странице
        try:
            checkbox = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//label[contains(text(), 'Verify you are human')]/preceding-sibling::input"))
            )
            human_like_click(checkbox, driver)
            print("Нашли чекбокс на основной странице")
            return True
        except:
            print("pass")

        print('pass')
        return False

    except Exception as e:
        print(f"Произошла ошибка: {e}")
        return False

async def get_seleniumbase_sb(url=None, headless=True, proxy=True):
    from pyvirtualdisplay import Display
    from seleniumbase import Driver

    driver_options = {
        'uc': True,
        'agent': ua.chrome,
        'log_cdp': True,  # Enable Chrome DevTools Protocol logging
        'no_sandbox': True,  # Required for Docker/CI environments
        'disable_gpu': True,  # Better for headless execution
        'pls': 'eager',  # Page load strategy: 'normal', 'eager', or 'none'
        'window_size': '1920,1080',  # Default window size
        'chromium_arg': [
            '--ignore-certificate-errors',
            '--disable-dev-shm-usage',
            '--disable-extensions',
            '--disable-infobars',
            '--start-maximized',
            '--disable-web-security'  # Optional: bypass some protections
        ]
    }

    if proxy:
        print('>>> Selenium PROXY...')
        proxy_host, proxy_port, login_proxy, proxy_port = await get_one_proxy()
        print(f'New One Proxy: {proxy_host}:{proxy_port}')
        proxy_string = f"{login_proxy}:{pass_proxy}@{proxy_host}:{proxy_port}"
        driver_options['proxy'] = proxy_string

    # else:
    #     print('>>> Selenium NO PROXY...')
    #     proxy_string = None

    if headless:
        disp = Display(visible=0, size=(1920, 1080))
        disp.start()

    driver = Driver(**driver_options)
    print('<<< Selenium connect...')

    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        '''
    })

    driver.execute_cdp_cmd('Network.enable', {})

    if url:
        driver.get(url)
        driver.wait_for_element("body", timeout=10)
        await asyncio.sleep(5)

    return driver

async def get_selenium_win(url=None, headless=True, proxy=True):

    from selenium_authenticated_proxy import SeleniumAuthenticatedProxy

    proxy_host, proxy_port = await get_one_proxy()
    print(proxy_host)
    proxy_string = f"http://{login_proxy}:{pass_proxy}@{proxy_host}:{proxy_port}"

    # Initialize Chrome options
    chrome_options = webdriver.ChromeOptions()
    # Set logging preferences for 'performance'
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})  # This is the new way for Selenium 4+

    # Initialize SeleniumAuthenticatedProxy
    proxy_helper = SeleniumAuthenticatedProxy(proxy_url=proxy_string)

    # Enrich Chrome options with proxy authentication
    proxy_helper.enrich_chrome_options(chrome_options)

    # Start WebDriver with enriched options
    driver = webdriver.Chrome(options=chrome_options)
    if url:
        driver.get(url)

    return driver

async def get_selenium_proxy(url=None, headless=True, proxy=True):
    from pyvirtualdisplay import Display
    driver_options = {
        'uc': True,
        'agent': ua.chrome,
        'headless': headless,
        'headless1': headless,
        'headless2': headless,
        'log_cdp': True,  # Enable Chrome DevTools Protocol logging
        'no_sandbox': True,  # Required for Docker/CI environments
        'disable_gpu': True,  # Better for headless execution
        'pls': 'eager',  # Page load strategy: 'normal', 'eager', or 'none'
        'window_size': '1920,1080'  # Default window size
    }

    if headless:
        print('- Virtual Display ON')
        display = Display(visible=0, size=(1920, 1080))  # Виртуальный дисплей
        display.start()

    if proxy:
        print('>>> Selenium PROXY...')
        proxy_host, proxy_port, proxy_login, proxy_pass = await get_one_proxy()

        print(f'New One Proxy: {proxy_host}:{proxy_port}')
        proxy_string = f"{proxy_login}:{proxy_pass}@{proxy_host}:{proxy_port}"
        driver_options['proxy'] = proxy_string

    else:
        print('>>> Selenium NO PROXY...')

    driver = Driver(**driver_options)
    print('<<< Selenium connect...')

    if url:
        # Если нужно использовать get, убедитесь что используете асинхронный метод
        driver.get(url)

    driver.execute_cdp_cmd('Network.enable', {})
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

async def get_playwright_anticloud(url, headless=True, proxy=None):
    print('>>> start PW AntiCloud')
    """
     :param url: url
     :param headless: headless (boot) headless=True
     :return:
     """
    from patchright.async_api import async_playwright, Browser, BrowserContext, Page

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            channel='chrome',
            headless=headless,
            proxy=None,
            args=[
                '--disable-blink-features=AutomationControlled',
            ]
        )
        context = await browser.new_context()

        # Assuming you want to return the first page for simplicity
        page = await context.new_page()
        await page.goto(url)

        await asyncio.sleep(10)

        print(await page.content())

        input('Next...')

        await asyncio.Future()

        # Return the Page object
        return page  # Added return statement

async def get_data_with_proxy(url, text_format=True):
    trying = 3
    for i in range(trying):
        print(f'--- Proxy try {i}')
        proxy_host, proxy_port, proxy_login, proxy_pass = await get_one_proxy()
        connector = ProxyConnector(proxy_type=ProxyType.HTTP,
                                   host=proxy_host,
                                   port=proxy_port,
                                   username=proxy_login,
                                   password=proxy_pass)

        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            print('--1--')
            try:
                async with session.get(url) as response:
                    print('--2--')
                    status_code = response.status
                    print("--- Status:", status_code)

                    if status_code == 403:
                        if i == trying - 1:
                            return None

                    elif status_code == 507:
                        if i == trying - 1:
                            return None

                    response.raise_for_status()
                    if text_format:
                        return await response.text()
                    else:
                        return await response.json()

                await asyncio.sleep(5)

            except asyncio.TimeoutError as TE:
                print(f"Error Proxy TE: {TE}")
                await asyncio.sleep(5)  # Ждем перед повторной попыткой

            except Exception as Ex:
                print(f"{i} Error Proxy Ex: {Ex}")
                await asyncio.sleep(5)

    return None

async def get_data_without_proxy(url, text_format=True):
    trying = 3
    headers = await gen_ua(url)

    for i in range(trying):
        print(f'- Without Proxy try {i}')
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            print('--1--')
            try:
                async with session.get(url) as response:
                    print('--2--')
                    status_code = response.status
                    print("Status:", status_code)

                    if status_code == 403:
                        if i == trying - 1:
                            return None

                    if status_code == 404:
                        if i == trying - 1:
                            return None

                    elif status_code == 507:
                        if i == trying - 1:
                            return None

                    response.raise_for_status()
                    if text_format:
                        return await response.text()
                    else:
                        return await response.json()

                await asyncio.sleep(5)

            except asyncio.TimeoutError as TE:
                print(f"- Error without Proxy TE: {TE}")
                await asyncio.sleep(5)  # Ждем перед повторной попыткой

            except Exception as Ex:
                print(f"- {i} Error without Proxy Ex: {Ex}")
                #print(await response.text())
                await asyncio.sleep(5)
    return None

async def get_selenium_sap(url=None, headless=True, proxy=True):
    """
    Selenium Authenticated Proxy Helper — это утилита Python, разработанная для бесшовной обработки аутентификации
    прокси при использовании Selenium WebDriver. Этот пакет генерирует расширение Chrome,
    которое заботится об аутентификации прокси, позволяя вам больше сосредоточиться на задачах веб-скрейпинга или
    автоматизации, не беспокоясь о тонкостях настройки прокси.
    https://github.com/freezingdata/selenium-authenticated-proxy
    Returns: driver
    """

    from selenium_authenticated_proxy import SeleniumAuthenticatedProxy

    proxy_host, proxy_port = await get_one_proxy()
    print(proxy_host)
    proxy_string = f"http://{login_proxy}:{pass_proxy}@{proxy_host}:{proxy_port}"

    # Initialize Chrome options
    chrome_options = webdriver.ChromeOptions()
    # Set logging preferences for 'performance'
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})  # This is the new way for Selenium 4+

    # Initialize SeleniumAuthenticatedProxy
    proxy_helper = SeleniumAuthenticatedProxy(proxy_url=proxy_string)

    # Enrich Chrome options with proxy authentication
    proxy_helper.enrich_chrome_options(chrome_options)

    # Start WebDriver with enriched options
    driver = webdriver.Chrome(options=chrome_options)
    if url:
        driver.get(url)

    return driver

def get_selenium_proxy_sync(url=None, headless=True, proxy=True):
        driver_options = {
            'uc': True,
            'headless': headless,
            'headless1': headless,
            'headless2': headless,
            'agent': ua.chrome,
            'log_cdp_events': True
        }

        if proxy:
            print('>>> Selenium PROXY...')
            proxy_host, proxy_port = asyncio.run(get_one_proxy())
            print(f'Proxy: {proxy_host}:{proxy_port}')
            proxy_string = f"{login_proxy}:{pass_proxy}@{proxy_host}:{proxy_port}"
            driver_options['proxy'] = proxy_string

        else:
            print('>>> Selenium NO PROXY...')

        driver = Driver(**driver_options)
        print('<<< Selenium connect...')

        if url:
            # Если нужно использовать get, убедитесь что используете асинхронный метод
            driver.get(url)

        return driver

async def get_patchright(url):
    from patchright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel='chrome',
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        page = await browser.new_page()

        await asyncio.sleep(10)
        await page.goto(url)

        input('wait..............')
        #await page.screenshot(path=f'example-{p.chromium.name}.png')
        await browser.close()

async def tst_proxy():
    proxy_host = '166.1.161.16'
    proxy_port = "20225"
    login_proxy = 'CAjuNdnZYnyj'
    pass_proxy = 'kostik777.08'

    url = "https://2gis.ru/firm/70000001045736119"

    connector = ProxyConnector(proxy_type=ProxyType.HTTP,
                               host=proxy_host,
                               port=proxy_port,
                               username=login_proxy,
                               password=pass_proxy)

    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:

        async with session.get(url) as response:
            status_code = response.status
            print("--- Status:", status_code)
            print(await response.text())

async def main():
    url = "https://2gis.ru/firm/70000001045736119"

    driver = await get_selenium_proxy(url, headless=False, proxy=True)

    print(driver.page_source)


if "__main__" in __name__:
    asyncio.run(main())
    #soup = asyncio.run(get_soup('https://irecommend.ru/content/uzhasnei-kompanii-ya-ne-vstrechal', proxy=False))
    #print(soup.title)