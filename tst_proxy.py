import os

import aiohttp
import asyncio
import requests
from dotenv import load_dotenv

from aiohttp_proxy import ProxyConnector, ProxyType

from utils.proxy_module import get_one_proxy

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

login_proxy = os.environ.get("LOGIN_PROXY")
pass_proxy = os.environ.get("PASS_PROXY")


async def get_data_with_proxy(url):
    r = requests.get(url)
    print(r.text)


    proxy_host, proxy_port = await get_one_proxy()
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
            print(response.text())




if "__main__" in __name__:
    asyncio.run(get_data_with_proxy('https://api.2ip.io'))