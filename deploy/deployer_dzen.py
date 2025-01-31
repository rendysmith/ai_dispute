import asyncio
import os

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

from utils.user_agent import get_selenium

header_text = 'Факт №1'
text_text = '''
В Древнем Египте кошки считались священными животными, и их убийство, даже случайное, каралось смертной казнью. 
Однако есть еще более интересный нюанс: когда в доме умирала кошка, все члены семьи в знак траура сбривали брови. 
Этот ритуал длился до тех пор, пока брови не отрастали снова. 
Кошки ассоциировались с богиней Бастет, которая символизировала домашний очаг, плодородие и защиту. 
Их настолько почитали, что во время войн египтяне иногда проигрывали сражения, 
потому что противники использовали кошек как "живой щит" — египтяне отказывались атаковать, чтобы не навредить священным животным.'''

async def deploy_dzen():
    profile_name = 'dzen_profile'

    # Инициализация драйвера
    url = 'https://dzen.ru/profile/editor/id/6790dbaf4abfd865fcff18ea/6790dcd0fa87ea6b3dfef17a/edit'
    driver = await get_selenium(url, headless=False, profile=profile_name)

    while True:
        try:
            boxs = driver.find_elements(By.CSS_SELECTOR, 'div[class="public-DraftStyleDefault-block public-DraftStyleDefault-ltr"]')
            print(len(boxs))
            boxs[0].click()
            break

        except:
            print('Wait...')
            await asyncio.sleep(3)

    print('- Header')
    boxs[0].send_keys(header_text)
    #boxs[1].click()

    print('- Text')
    boxs[1].send_keys(text_text)

    input('next?...')

    print('- Publish')
    deploy_button = driver.find_element(By.CSS_SELECTOR, 'button[data-testid="article-publish-btn"][type="button"]')
    deploy_button.click()

    while True:
        try:
            print('- Checkbox')
            checkbox_button = driver.find_element(By.CSS_SELECTOR, 'input[class][type="checkbox"]')
            checkbox_button.click()
            break

        except:
            print('Wait...')
            await asyncio.sleep(3)

    await asyncio.sleep(3)

    continue_button = driver.find_element(By.CSS_SELECTOR, 'button[class][type="submit"]')
    continue_button.click()

    while True:
        try:
            publish_btn = driver.find_element(By.CSS_SELECTOR, 'button[class][data-testid="publish-btn"][type="submit"]')
            publish_btn.click()
            break

        except:
            print('Wait...')
            await asyncio.sleep(3)








    input('wait...')


if "__main__" in __name__:
    asyncio.run(deploy_dzen())
