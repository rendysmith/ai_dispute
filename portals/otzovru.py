import asyncio

from selenium.webdriver.common.by import By

from utils.user_agent import get_selenium_proxy, get_soup

async def get_feedback_otzovru(url):
    soup = await get_soup(url, proxy=False)
    title = soup.find('h1', {"class":"element_name", "itemprop":"name"}).text

    text = soup.find('span', {"class":"comment description", "itemprop":"reviewBody"}).text

    try:
        advantages = soup.find('div', {"class":"advantages"}).text
    except:
        advantages = ''

    try:
        disadvantages = soup.find('div', {"class":"disadvantages"}).text
    except:
        disadvantages = ''

    feedback = f'{title}\n{text}\n{advantages}\n{disadvantages}'

    # feedback = soup.find('div', {'class': 'comment_row'}).text
    print(feedback)

    return feedback




async def blocks_otzovru(driver, url):
    driver.get(url)
    await asyncio.sleep(5)
    blocks = driver.find_elements(By.CSS_SELECTOR, 'div[class="comment_row "]')
    return blocks

async def main():
    # driver = await get_selenium_proxy(headless=False, proxy=False)
    # url = 'https://www.otzyvru.com/servis-poiska-vrachey-docdoc?sort=rating_asc'
    # await blocks_otzovru(driver, url)
    url = 'https://www.otzyvru.com/servis-poiska-vrachey-docdoc/review-1103642'
    url = 'https://www.otzyvru.com/servis-poiska-vrachey-docdoc/review-431934'
    #url = 'https://www.otzyvru.com/servis-poiska-vrachey-docdoc/review-346862'
    #url = 'https://www.otzyvru.com/servis-poiska-vrachey-docdoc/review-339070'
    await get_feedback(url)


if "__main__" in __name__:
    asyncio.run(main())


