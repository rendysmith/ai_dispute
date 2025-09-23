import asyncio

from selenium.webdriver.common.by import By

from utils.user_agent import get_selenium_proxy


async def blocks_otzovru(driver, url):
    driver.get(url)
    await asyncio.sleep(5)
    blocks = driver.find_elements(By.CSS_SELECTOR, 'div[class="comment_row "]')
    return blocks

async def main():
    driver = await get_selenium_proxy(headless=False, proxy=False)
    url = 'https://www.otzyvru.com/servis-poiska-vrachey-docdoc?sort=rating_asc'
    await blocks_otzovru(driver, url)


if "__main__" in __name__:
    asyncio.run(main())


