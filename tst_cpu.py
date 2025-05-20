import asyncio
import os
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from utils.proxy_bridge import get_one_proxy

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

login_proxy = os.environ.get("LOGIN_PROXY")
pass_proxy = os.environ.get("PASS_PROXY")

async def func_1():

    proxy_host, proxy_port = await get_one_proxy()
    print(proxy_host)

    # Define custom options for the Selenium driver
    options = Options()
    proxy_server_url = f"https://{login_proxy}:{pass_proxy}@{proxy_host}:{proxy_port}"
    print(proxy_server_url)
    options.add_argument(f'--proxy-server={proxy_server_url}')

    # Create the ChromeDriver instance with custom options
    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=options
    )
    driver.get("2ip.ru")

    input(1)


async def get_selenium_win(url=None, headless=True, proxy=True):
    proxy = "username:password@proxy_address:proxy_port"
    proxy_host, proxy_port = await get_one_proxy()
    print(proxy_host)
    proxy = f'{login_proxy}:{pass_proxy}@{proxy_host}:{proxy_port}'
    print(proxy)

    chrome_options = Options()
    chrome_options.add_argument(f'--proxy-server=http://{proxy}')

    driver = webdriver.Chrome(options=chrome_options)
    driver.get("2ip.ru")
    input(2)

    if url:
        driver.get(url)

    return driver

async def get_seleniumbase_SB(url=None, headless=True, proxy=True):
    from seleniumbase import SB

    from fake_useragent import UserAgent
    ua = UserAgent()


    print('>>> Selenium PROXY...')
    proxy_host, proxy_port = await get_one_proxy()
    print(f'New One Proxy: {proxy_host}:{proxy_port}')
    proxy_string = f"{login_proxy}:{pass_proxy}@{proxy_host}:{proxy_port}"


    with SB(proxy=proxy_string, headless=headless, agent=ua.chrome) as sb:
        #sb.__enter__()  # вручную запускаем контекст

        sb.driver.get("2ip.ru")

        input(3)

        # if url:
        #     sb.driver.get(url)
        #
        # return sb

if "__main__" in __name__:
    asyncio.run(func_1())
    asyncio.run(get_selenium_win())
    asyncio.run(get_seleniumbase_SB())
