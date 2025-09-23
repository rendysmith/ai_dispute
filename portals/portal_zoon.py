from datetime import datetime

import asyncio

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

from utils.user_agent import get_soup, get_selenium_proxy



async def zoon_blocks(driver, url, max_rating):
    # driver.get(url)
    # await asyncio.sleep(5)

    print('Click: Reviews')

    try:
        driver.find_element(By.CSS_SELECTOR, 'a[data-id="reviews"][data-type="reviews"]').click()
        print('- Click: R1')

    except:
        driver.find_elements(By.CSS_SELECTOR, 'span[class="service-block-nav-item-text"]')[1].click()
        print('- Click: R2')

    await asyncio.sleep(5)

    print('- scrollTo: ')
    n = 0
    while n < 10:
        #driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        driver.execute_script("window.scrollBy(0, window.innerHeight);")

        try:
            driver.find_element(By.CSS_SELECTOR, 'a[data-uitest="show-more-comments-button"]').click()
            print('Click: M1')
            break

        except:
            try:
                driver.find_element(By.CSS_SELECTOR, 'div[class="comments-next js-show-more-box"]').click()
                print('Click: M2')
                break

            except:
                #print(driver.page_source)
                blocks = driver.find_elements(By.CSS_SELECTOR,
                                              'div[class="comment-item__container js-comment-container"][itemprop="review"]')
                print("Len_b:", len(blocks))
                n+=1
                print(f'- except {n}')

    await asyncio.sleep(3)

    blocks = driver.find_elements(By.CSS_SELECTOR, 'div[class="comment-item__container js-comment-container"][itemprop="review"]')
    print("Len_b:", len(blocks))

    datas = {
        "Дата": [],
        "Текст": [],
        "Url": [],
        "Автор": [],
        "Оценка": [],
    }

    for block in blocks:
        rating = int(block.find_element(By.CSS_SELECTOR, 'meta[itemprop="ratingValue"]').get_attribute("content"))
        print("rating: ", rating)

        if rating > max_rating:
            continue

        date_str = block.find_element(By.CSS_SELECTOR,  'meta[itemprop="datePublished"]').get_attribute('content')
        dt = datetime.fromisoformat(date_str)
        formatted_date = dt.strftime("%d.%m.%Y")
        #print(formatted_date)

        feedback = block.find_element(By.CSS_SELECTOR, 'div[class="comment-item__body js-comment-text"]').text
        #print(feedback)

        data_id = block.get_attribute('data-id')
        url_answer = f'{url}#comment{data_id}'
        #print(url_answer)

        author = block.find_element(By.CSS_SELECTOR, 'span[itemprop="name"]').text
        #print(author)

        datas['Дата'].append(formatted_date)
        datas['Текст'].append(feedback)
        datas['Url'].append(url_answer)
        datas['Автор'].append(author)
        datas['Оценка'].append(rating)

    print(f'Len: {len(datas["Дата"])}')
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
    url = "https://zoon.ru/msk/internet/internet-portal_po_poisku_vrachej_sberzdorove"

    driver = await get_selenium_proxy(url, headless=False, proxy=False)
    datas = await zoon_blocks(driver, url, 3)
    print(datas)

if "__main__" in __name__:
    asyncio.run(main())


