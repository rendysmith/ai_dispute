import asyncio

from utils.user_agent import get_selenium_proxy, get_soup


async def main():
    soup = await get_soup('https://api.ipify.org')
    print(soup)

    url = 'https://2gis.ru/yaroslavl/firm/70000001045733822/tab/reviews'

    driver = await get_selenium_proxy(url)
    await asyncio.sleep(15)
    print(driver.page_source)

if "__main__" in __name__:
    asyncio.run(main())