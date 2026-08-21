import asyncio
import logging
import os
import re

import aiohttp
import requests
from aiohttp_proxy import ProxyConnector, ProxyType
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fake_useragent import UserAgent
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from utils.proxy_module import get_one_proxy

os.environ['DISABLE_COLIED_TRACEBACK'] = '1'
os.environ["DISABLE_COLORAMA"] = "1"
os.environ["SELENIUMBASE_COLOR"] = "0"

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

ua = UserAgent()


async def clean_html(raw: str) -> str:
    import html
    # убираем теги
    text = BeautifulSoup(raw, "html.parser").get_text(separator="\n")
    # декодируем символы
    return html.unescape(text).strip()


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
        host, port, login_proxy, pass_proxy = await get_one_proxy()
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


async def get_soup_bs4(url, only_pars=False):
    """
    only_pars=False: загружает страницу и возвращает soup
    only_pars=True: url - это HTML-строка, парсим её
    """
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


async def get_soup(url, only_text=True, proxy=True, proxy_type=None):
    '''
    only_text = True - получить данные в SOUP формате
    only_text = False - в формате JSON
    '''

    if only_text:  # Получить только текст
        if proxy:
            r_text = await get_data_with_proxy(url, proxy_type)
            print('Soup Proxy!')

            if not r_text:
                print('aiohttp proxy failed, trying curl_cffi fallback...')
                return await get_soup_curl_cffi(url, dict_type=False, proxy=proxy)

        else:
            r_text = await get_data_without_proxy(url)
            if not r_text:
                print('aiohttp without proxy failed, trying curl_cffi fallback...')
                return await get_soup_curl_cffi(url, dict_type=False, proxy=proxy)

        soup = await get_soup_bs4(r_text, only_pars=True)
        return soup

    else:  # Получить json()
        if proxy:
            r_json = await get_data_with_proxy(url, text_format=False)
            if not r_json:
                print('aiohttp proxy JSON failed, trying curl_cffi fallback...')
                return await get_soup_curl_cffi(url, dict_type=True, proxy=proxy)
        else:
            r_json = await get_data_without_proxy(url, text_format=False)
            if not r_json:
                print('aiohttp without proxy JSON failed, trying curl_cffi fallback...')
                return await get_soup_curl_cffi(url, dict_type=True, proxy=proxy)
        return r_json


async def get_playwright(url=False, headless=True, proxy=True, proxy_type=None, blocked_resource=True, stealth=False):
    if proxy:
        host, port, login, password = await get_one_proxy(proxy_type)

        proxy = {
            "server": f"http://{host}:{port}",
            "username": login,  # можно опустить
            "password": password  # можно опустить
        }
    else:
        proxy = None

    p = await async_playwright().start()
    browser = await p.chromium.launch(
        headless=headless,
        proxy=proxy,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
    )
    context = await browser.new_context(
        user_agent=str(ua),
        viewport={"width": 1366, "height": 768},
        locale="ru-RU"
    )
    await context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    if stealth:
        await Stealth().apply_stealth_async(context)

    page = await context.new_page()

    if blocked_resource:
        # Список типов ресурсов, которые нужно блокировать
        BLOCKED_RESOURCE_TYPES = ["image", "media", "font", "stylesheet"]

        # Список частей URL, которые нужно блокировать (для трекеров)
        BLOCKED_URL_PARTS = [
            "mail.ru/tracker",
            "google-analytics.com",
            "mc.yandex.ru"
        ]

        async def block_requests(route):
            resource_type = route.request.resource_type
            request_url = route.request.url

            # 1. Блокировка по типу ресурса
            if resource_type in BLOCKED_RESOURCE_TYPES:
                await route.abort()
                return

            # 2. Блокировка по URL (для трекеров)
            if any(part in request_url for part in BLOCKED_URL_PARTS):
                await route.abort()
                return

            # 3. Разрешение всех остальных запросов
            await route.continue_()

        # Регистрируем расширенный обработчик
        # **/* означает перехват всех URL
        await page.route("**/*", block_requests)

    if url:
        await page.goto(url, wait_until='domcontentloaded')
        await page.wait_for_timeout(5000)  # имитация паузы

    return p, browser, context, page


async def get_playwright_irec(url, proxy=None, proxy_type=None):
    """
    Загружает страницу через Playwright headless + stealth.
    Оптимизировано для irecommend.ru — ждёт 5 сек после domcontentloaded
    для прохождения JS-captcha-checker.

    :param url: URL для загрузки
    :param proxy: словарь прокси {'host': str, 'port': str, 'login': str, 'password': str}
                  или True — берёт прокси из БД по proxy_type
    :param proxy_type: тип прокси для БД (например 'mobile')
    :return: HTML текст страницы (str) или None при ошибке
    """
    pw_proxy = None

    if proxy is True:
        host, port, login, password = await get_one_proxy(proxy_type)
        pw_proxy = {
            "server": f"http://{host}:{port}",
            "username": login,
            "password": password,
        }
    elif isinstance(proxy, dict):
        host = proxy.get('host')
        port = proxy.get('port')
        login = proxy.get('login')
        password = proxy.get('password')
        pw_proxy = {
            "server": f"http://{host}:{port}",
            "username": login,
            "password": password,
        }

    p = await async_playwright().start()
    browser = await p.chromium.launch(
        headless=True,
        proxy=pw_proxy,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
    )
    context = await browser.new_context(
        user_agent=str(ua),
        viewport={"width": 1366, "height": 768},
        locale="ru-RU",
    )
    await Stealth().apply_stealth_async(context)

    page = await context.new_page()

    # Блокируем лишнее для скорости
    BLOCKED_RESOURCE_TYPES = ["image", "media", "font", "stylesheet"]

    async def block_requests(route):
        if route.request.resource_type in BLOCKED_RESOURCE_TYPES:
            await route.abort()
            return
        await route.continue_()

    await page.route("**/*", block_requests)

    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(5000)
        html = await page.content()
        return html
    except Exception as e:
        logging.warning(f"get_playwright_irec error: {e}")
        return None
    finally:
        await browser.close()
        await p.stop()


async def get_data_with_proxy(url, text_format=True, proxy_type=None):
    """
    text_format: True - text
    text_format: False - json()
    """
    trying = 5
    for i in range(trying):
        print(f'--- Proxy try {i}')
        proxy_host, proxy_port, proxy_login, proxy_pass = await get_one_proxy(proxy_type)
        print("ProxyHost:", proxy_host)

        if not proxy_host:
            return None

        connector = ProxyConnector(proxy_type=ProxyType.HTTP,
                                   host=proxy_host,
                                   port=proxy_port,
                                   username=proxy_login,
                                   password=proxy_pass)

        headers = {
            'User-Agent': ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        }

        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(connector=connector,
                                         timeout=timeout,
                                         headers=headers) as session:
            print('--1--')
            try:
                async with session.get(url) as response:
                    print('--2--')
                    status_code = response.status
                    print("--- Status:", status_code)

                    if status_code == 400:
                        logging.info('400 Bad Request (Плохой запрос)')
                        if i == trying - 1:
                            return None

                    elif status_code == 403:
                        logging.info('403 Forbidden (Запрещено)')
                        if i == trying - 1:
                            return None

                    elif status_code == 507:
                        logging.info('507 Insufficient Storage (Недостаточно места)')
                        if i == trying - 1:
                            return None

                    elif status_code == 521:
                        logging.error('521 Web Server Is Down (Целевой сервер недоступен)')
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
                await asyncio.sleep(5)
    return None
