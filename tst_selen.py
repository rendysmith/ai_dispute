import asyncio

from utils.user_agent import get_selenium_proxy, get_soup, ua

async def get_playwright(url, headless=True, proxy=False):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent=str(ua),
            viewport={"width":1366,"height":768},
            locale="en-US"
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        page = await context.new_page()
        await page.goto(url)
        await page.wait_for_timeout(1000)
        content = await page.content()

        await browser.close()
        return content



async def main():
    soup = await get_soup('https://api.ipify.org')
    print(soup)

    url = 'https://2gis.ru/yaroslavl/firm/70000001045733822/tab/reviews'

    driver = await get_selenium_proxy(url)
    await asyncio.sleep(15)
    print('\n********1********\n', driver.page_source)

    # driver = await get_selenium_proxy(url)
    # await asyncio.sleep(15)
    # print('\n********2********\n', driver.page_source)

    driver_content = await get_playwright(url)
    await asyncio.sleep(15)
    print('\n********3********\n', driver_content)

if "__main__" in __name__:
    asyncio.run(main())