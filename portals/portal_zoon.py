import asyncio

from utils.user_agent import get_soup, get_selenium_proxy


async def zoon_blocks(url):
    driver = await get_selenium_proxy(url, headless=False, proxy=False)


if "__main__" in __name__:
    url = "https://zoon.ru/msk/banks/lizingovaya_kompaniya_sberlizing/"
    asyncio.run(zoon_blocks(url))

