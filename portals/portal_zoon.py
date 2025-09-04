from datetime import datetime

import asyncio

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

from utils.user_agent import get_soup, get_selenium_proxy



async def zoon_blocks(driver, url):
    # driver.get(url)
    # await asyncio.sleep(5)

    print('Clock 1')

    try:
        driver.find_element(By.CSS_SELECTOR, 'span[class="service-block-nav-item-text"]').click()

    except:
        driver.find_element(By.CSS_SELECTOR, 'a[data-id="reviews"][data-type="reviews"]').click()

    await asyncio.sleep(5)
    print('Clock 1')

    print('Clock 2')
    # Ждём кликабельности кнопки "Показать ещё"
    # more_comments = WebDriverWait(driver, 10).until(
    #     EC.element_to_be_clickable((By.CSS_SELECTOR, 'span[class="service-block-nav-item-text"]'))
    # )
    #
    # # Прокручиваем к элементу и кликаем через ActionChains
    # driver.execute_script("arguments[0].scrollIntoView(true);", more_comments)
    #await asyncio.sleep(3)  # небольшая пауза после прокрутки
    #ActionChains(driver).move_to_element(more_comments).click().perform()

    try:
        driver.find_element(By.CSS_SELECTOR, 'a[data-uitest="show-more-comments-button"]').click()

    except:
        try:
            driver.find_element(By.CSS_SELECTOR, 'div[class="comments-next js-show-more-box"]').click()
        except:
            #print(driver.page_source)
            print('- except 2')

    print('Clock 2')

    await asyncio.sleep(3)

    blocks = driver.find_elements(By.CSS_SELECTOR, 'li[class="comment-item js-comment "]')
    print("Len_b:", len(blocks))

    datas = {
        "Дата": [],
        "Текст": [],
        "Url": [],
        "Автор": [],
        "Оценка": [],
    }

    for block in blocks:
        date_str = block.find_element(By.CSS_SELECTOR,  'meta[itemprop="datePublished"]').get_attribute('content')
        dt = datetime.fromisoformat(date_str)
        formatted_date = dt.strftime("%d.%m.%Y")
        print(formatted_date)

        feedback = block.find_element(By.CSS_SELECTOR, 'span[class="js-comment-content"]').text
        print(feedback)

        data_id = block.get_attribute('data-id')
        url_answer = f'{url}#comment{data_id}'
        print(url_answer)

        author = block.get_attribute('data-author')
        print(author)

        rating = int(block.find_element(By.CSS_SELECTOR, 'meta[itemprop="ratingValue"]').get_attribute("content"))
        print(rating)

        datas['Дата'].append(formatted_date)
        datas['Текст'].append(feedback)
        datas['Url'].append(url_answer)
        datas['Автор'].append(author)
        datas['Оценка'].append(rating)

    return datas




async def zoon_blocks_soup(url):
    soup = await get_soup(url, proxy=False)
    blocks = soup.find_all('li', {'class': 'comment-item js-comment'})

    datas = {
        "Дата": [],
        "Текст": [],
        "Url": [],
        "Автор": [],
        "Оценка": [],
    }

    for block in blocks:
        date_str = block.find('meta', {"itemprop": "datePublished"}).get('content')
        dt = datetime.fromisoformat(date_str)
        formatted_date = dt.strftime("%d.%m.%Y")
        print(formatted_date)

        feedback = block.find('span', {"class": "js-comment-content"}).text
        print(feedback)

        data_id = block.get('data-id')
        url_answer = f'{url}#comment{data_id}'
        print(url_answer)

        author = block.get('data-author')
        print(author)

        rating = block.find('meta', {"itemprop": "ratingValue"}).get("content")
        print(rating)

        datas['Дата'].append(formatted_date)
        datas['Текст'].append(feedback)
        datas['Url'].append(url_answer)
        datas['Автор'].append(author)
        datas['Оценка'].append(rating)

    return datas

    for block in blocks:
        print("\n-------------------", block)



    #driver = await get_selenium_proxy(url, headless=False, proxy=False)

async def main():
    url = "https://zoon.ru/msk/banks/lizingovaya_kompaniya_sberlizing/"

    driver = await get_selenium_proxy(url, headless=False, proxy=False)
    await zoon_blocks(driver, url)

if "__main__" in __name__:
    asyncio.run(main())


