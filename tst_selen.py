import asyncio

from portals.portal_2gis import get_key
from utils.user_agent import get_selenium_proxy, get_soup, ua, get_playwright

async def log_all_requests(page, wait_time: int = 15000):
    """Ловит и выводит все запросы, чтобы понять, какие идут при загрузке."""
    async def on_request(request):
        initiator = request.resource_type.upper()
        method = request.method
        domain = request.url

        print(method, domain)

    page.on("request", on_request)

    # ждем, пока страница все подгрузит
    await page.wait_for_timeout(wait_time)


async def catch_xhr_requests(browser):
    context = await browser.new_context()
    page = await context.new_page()

    # Подключаем CDP (как Network.enable в Selenium)
    client = await context.new_cdp_session(page)
    await client.send("Network.enable")

    results = []

    @client.on("Network.requestWillBeSent")
    async def on_request(event):
        req = event.get("request", {})
        url_ = req.get("url", "")
        if "key=" in url_:
            print(f"📡 {req.get('method')} {url_}")
            results.append(req)

    await page.goto(url)
    await asyncio.sleep(wait_time / 1000)

    await browser.close()
    return results








async def main():
    # soup = await get_soup('https://api.ipify.org')
    # print(soup)

    url = 'https://2gis.ru/yaroslavl/firm/70000001045733822/tab/reviews'

    # driver = await get_selenium_proxy(url)
    # await asyncio.sleep(15)
    # print('\n********1********\n', driver.page_source)

    # driver = await get_selenium_proxy(url)
    # await asyncio.sleep(15)
    # print('\n********2********\n', driver.page_source)

    p, browser, context, page = await get_playwright(url, proxy=False)
    content = await page.content()
    #print(content)

    id_org, key = await get_key(content)
    print(id_org, key)

    input()

    results = await catch_xhr_requests(browser)
    print(results)
    input()

    await log_all_requests(page)
    api_calls = await catch_xhr_requests(page, "public-api.reviews.2gis.com")
    print(api_calls)
    await browser.close()
    await p.stop()

    # await asyncio.sleep(15)

    # print('\n********3********\n', driver_content)

if "__main__" in __name__:
    asyncio.run(main())