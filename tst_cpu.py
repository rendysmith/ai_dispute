import os
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

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
    options.add_argument(f'--proxy-server={proxy_server_url}')

    # Create the ChromeDriver instance with custom options
    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=options
    )

    input(1)


async def get_selenium_win(url=None, headless=True, proxy=True):
    proxy = "username:password@proxy_address:proxy_port"
    proxy_host, proxy_port = await get_one_proxy()
    print(proxy_host)
    proxy = f'{login_proxy}:{pass_proxy}@{proxy_host}:{proxy_port}'

    chrome_options = Options()
    chrome_options.add_argument(f'--proxy-server=http://{proxy}')

    driver = webdriver.Chrome(options=chrome_options)
    input(2)

    if url:
        driver.get(url)

    return driver
