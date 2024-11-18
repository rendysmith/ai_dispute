import os
import textwrap
import time
from datetime import datetime, timedelta

import asyncio
import random

import pandas as pd
from dotenv import load_dotenv
from selenium.common import NoSuchWindowException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By


from utils.ai_module import generate_and_white
from utils.central_module import wait_for_portal, proxy_status, get_local_ip
from utils.constants import TABLES_LIST
from utils.gs_editor import append_data_to_sheet_scope, pars_url, get_service, get_table_scope, \
    append_data_to_sheet_cell, write_log_sheet
from utils.user_agent import extract_main_site, get_selenium_proxy

from threading import Thread

#os.environ['TERM'] = 'xterm'

current_date = datetime.now()
record_date = current_date.strftime("%d.%m.%Y")

corn_folder = os.path.dirname(os.path.dirname(__file__))

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)
days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))
ss_id = TABLES_LIST['zoom']

local_ip = asyncio.run(get_local_ip())

if '176.124.192' in local_ip:
    headless = False
    proxy_on = True

else:
    headless = False
    proxy_on = False

image_path = os.path.join(corn_folder, 'temp/image_to_find.png')

async def clicker_pyautogui():
    import pyautogui
    # Загрузка изображения искомого элемента

    while True:
        try:
            # Поиск на экране и нажатие
            element_location = pyautogui.locateCenterOnScreen(image_path, confidence=0.8)  # Уверенность можно менять

            if element_location is not None:
                pyautogui.click(element_location)
                print("Элемент найден и нажато!")
            else:
                print("Элемент не найден. 1")

        except:
            print("Элемент не найден. 2")

        await asyncio.sleep(5)

async def clicker_pyscreeze():
    import pyscreeze
    import pyautogui

    while True:
        try:
            # Ищем изображение на экране
            location = pyscreeze.locateOnScreen(image_path, confidence=0.8)

            if location is not None:
                print(f"Найдено изображение в позиции: {location}")

                # Получаем центр найденного изображения
                center_x = location.left + (location.width / 2)
                center_y = location.top + (location.height / 2)

                # Кликаем по центру
                pyautogui.click(center_x, center_y)
                print(f"Клик выполнен по координатам: {center_x}, {center_y}")
                return True
            else:
                print("Изображение не найдено")
                return False

        except Exception as e:
            print(f"Произошла ошибка: {e}")
            return False

        time.sleep(5)

async def async_find_and_click():
    import pyautogui
    import pyscreeze

    print('- Start Clicker!')

    def sync_find_and_click():
        while True:
            try:
                location = pyscreeze.locateOnScreen(image_path)
                if location:
                    center_x = location.left + (location.width / 2)
                    center_y = location.top + (location.height / 2)
                    pyautogui.click(center_x, center_y)
                    print('--- Click ->>>')

            except Exception as e:
                print(f"Ошибка: {e}")

            time.sleep(5)

        # Выполняем синхронную функцию в отдельном потоке
    return await asyncio.to_thread(sync_find_and_click)

async def clicker_autoit_w():
    from autoit import autoit as auto

    while True:
        # Поиск изображения
        if auto.pixel_search(image_path):
            x, y = auto.mouse_get_pos()
            auto.mouse_click("left", x, y)
            print('--- Click checkbox')

        else:
            print('--- NO checkbox')

        await asyncio.sleep(5)

async def clicker_pil():
    from PIL import Image, ImageGrab
    import numpy as np
    from pynput.mouse import Controller

    while True:
        print('--- Click checkbox')
        mouse = Controller()
        template = Image.open(image_path)
        screenshot = ImageGrab.grab()

        # Реализация поиска
        # После нахождения:
        mouse.position = (x, y)
        mouse.click()
        await asyncio.sleep(5)

async def check_irecommend(service, link, pattern, criteria, ss_id, project, driver):
    print(f'\nLink: {link}')
    try:
        driver.get(link)
        print('Driver OK')

    except:
        driver = await get_selenium_proxy(headless=headless, proxy=proxy_on)
        driver.get(link)
        print('New Driver OK')

    await wait_for_portal() #Время ожидания
    #page_source = driver.page_source
    #print(page_source)
    #----------------------------------------------------------------
    #print('Старт clicker...')
    #driver = await click_checkbox(driver)
    #----------------------------------------------------------------

    if 'new=1' not in link:
        n = 0
        while n < 10:
            print('- Поиск TOP страницы, если мы еще не на ней.')
            try:
                try:
                    top_block_content = driver.find_element(By.CSS_SELECTOR, 'a[class=" active"]')
                    top_block = top_block_content.get_attribute('href')
                    top_url = top_block + "?new=1"
                    print('- 1.1 Top url', top_url)
                    break

                except:
                    top_block_content = driver.find_element(By.CSS_SELECTOR, 'a[class="active"]')
                    top_block = top_block_content.get_attribute('href')
                    top_url = top_block + "?new=1"
                    print('- 1.2 Top url', top_url)
                    break


            except Exception as Ex1:
                try:
                    #traceback.print_exc()
                    top_block_content = driver.find_element(By.CSS_SELECTOR, 'div.description')
                    #print(top_block_content.get_attribute("outerHTML"))

                    top_block_get = top_block_content.find_element(By.CSS_SELECTOR, 'a[href]')
                    top_block = top_block_get.get_attribute('href')
                    top_url = top_block + "?new=1"
                    print('- 2 Top url', top_url)
                    break
                    #----------------------------------------------------------------
                except Exception as Ex2:
                    print(f'Error Ex2: {Ex2}')
                    return None

            except NoSuchWindowException as NSEE:
                print(f'Error NSEE: {NSEE}')
                return None

            except:
                print(f'--- driver refresh')
                driver.refresh()
                await asyncio.sleep(5)
                n += 1

                if n == 10:
                    return None

        datas = {'project': project,
                 'url': link,
                 'top_url': top_url}

        #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        await append_data_to_sheet_scope(service, ss_id, 'unique_url', datas)
        print('-- Record TOP link')

        try:
            driver.get(link)
            print('Driver OK')

        except:
            driver = await get_selenium_proxy(headless=headless, proxy=proxy_on)
            driver.get(link)
            print('New Driver OK')

        await wait_for_portal()  # Время ожидания

    else:
        print('- Это уже TOP страница.')

    print('- Get Blocks')
    n = 0
    len_b = 0
    while n < 10:
        try:
            print(f'- Search blocks {n}')
            #WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-type="1"]')))
            driver.execute_script("window.scrollBy(0, 500);")  # Скроллит вниз на 500 пикселей
            #print('- 1')
            blocks = driver.find_elements(By.CSS_SELECTOR, 'div[data-type="1"]')
            #print('- 2')
            len_b = len(blocks)
            print('Len_b =', len_b)
            break

        except:
            #driver.refresh()
            await asyncio.sleep(5)
            n += 1

    if len_b == 0:
        print('Len_b =', len_b)
        return

    links = await pars_url(service, ss_id, project)
    domen = await extract_main_site(link)

    for block in blocks:
        print('****************************')
        url_n_content = block.find_element(By.CSS_SELECTOR, 'a.reviewTextSnippet')
        url_n = url_n_content.get_attribute('href')
        url_answer = domen + url_n
        #print(url_answer)

        if url_answer in links:
            print('Отзыв уже есть в таблице')
            continue

        try:
            date = block.find_element(By.CSS_SELECTOR, "div.created").text
            target_date = datetime.strptime(date, "%d.%m.%Y")

        except:
            date_1 = block.find_element(By.CSS_SELECTOR, "div.created")
            date = date_1.find_element(By.CSS_SELECTOR, "span.date-created").text
            target_date = datetime.strptime(date, "%d.%m.%Y")

        if (current_date - target_date) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней = {date}.')
            return "Next..."

        author = block.find_element(By.CSS_SELECTOR, "div.authorName").text

        title = block.find_element(By.CSS_SELECTOR, "div.reviewTitle").text
        title_txt = block.find_element(By.CSS_SELECTOR, "span.reviewTeaserText").text

        feedback = f"""
        {title}
        {title_txt}
        """
        feedback = textwrap.dedent(feedback)
        #print(feedback)

        formatted_date = date

        await generate_and_white(service=service,
                                 url_answer=url_answer,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)

    return 'OK!'

async def main_irecommend():
    proxy_active = await proxy_status()
    print(f'+ Proxy status: {proxy_active}')

    driver = None
    if proxy_active == 'Active':
        driver = await get_selenium_proxy(headless=headless, proxy=proxy_on)

    local_ip = await get_local_ip()
    print('local_ip', local_ip)

    service = await get_service()
    df = await get_table_scope(service, ss_id, 'zoom')
    #print(df)
    idx_num_row = df.index[df['Проект'] == 'Кол-во строк'].tolist()[0]
    #print(idx_num_row)
    df_counts = pd.Series(df.iloc[idx_num_row].values, index=df.columns).reset_index()
    df_counts[0] = pd.to_numeric(df_counts[0], errors='coerce')
    # Удаляем строки с NaN значениями в указанной колонке
    df_counts = df_counts.dropna(subset=[0])
    df_counts = df_counts.sort_values(by=0)
    #print(df_counts)

    list_ = df_counts['index'].to_list()
    #print(list_)
    #random.shuffle(list_)

    df_uniq = await get_table_scope(service, ss_id, 'unique_url')

    df_logs = await get_table_scope(service, ss_id, 'logs')
    #print(df_logs)

    for project in list_:
        if 'Проект' in project:
            continue

        #Если дата не совпадает с сегодняшней
        host_logs = ''
        project_irecommend = f'irecommend_{project}'
        filtered_logs = df_logs[df_logs['service_name'] == project_irecommend]
        if not filtered_logs.empty:
            idx_logs = filtered_logs.index[0]

            if proxy_active != 'Active':
                await append_data_to_sheet_cell(service, ss_id, 'logs', 'proxy_status', idx_logs + 2, f'Proxy {proxy_active}')
                break

            else:
                await append_data_to_sheet_cell(service, ss_id, 'logs', 'proxy_status', idx_logs + 2,
                                                f'Proxy {proxy_active}')

            #Пропуск по дате
            date_logs = df_logs.loc[idx_logs, 'date']
            if date_logs == record_date:
                #print()
                continue

        #
        #     #Пропуск по IP
        #     host_logs = df_logs.loc[idx_logs, 'reserve']
        #     if host_logs != local_ip:
        #         print('Skip:', host_logs, local_ip)
        #         continue
        #
        # else:
        #     print(f"No logs found for service: {project}")


        df_mini = df[project]
        #print(len(df_mini))

        df_mini_pattern = df_mini[df_mini.str.contains('Пример реакции', na=False)]
        df_mini_criteria = df_mini[df_mini.str.contains('Особые критерии', na=False)]

        # Filter rows that contain 'http://'
        df_mini = df_mini[df_mini.str.contains('http', na=False)]

        # Remove duplicates
        # Удаляем дубликаты
        df_mini = df_mini.drop_duplicates().reset_index()

        df_link_list = df_mini[project].to_list()
        irec_link = [i for i in df_link_list if 'irecommend' in i]
        len_irec = len(irec_link)
        if len_irec == 0:
            print(f'{project} next...')
            continue

        print(f'\n ---> {project} Irec link = {len_irec} <---')

        random.shuffle(df_link_list)

        len_df = len(df_link_list)
        print(f'\n========================= Project = {project} = Len ({len_df})==============================')

        start_time = time.time()
        list_links = []

        record = False
        for idx, link in enumerate(df_link_list):
            left = len_df - df_link_list.index(link)
            print(
                f'\n*************************{idx}*({left})*{project}*************************\n----------------- {link} ----------------')

            if 'irecommend' in link:
                record = True
                top_df = df_uniq[(df_uniq['project'] == project) & (df_uniq['url'] == link)].reset_index(drop=True)
                # print(top_df)

                if not top_df.empty:
                    print('Есть общая ссылка на статью')
                    link = top_df.loc[0, 'top_url']

                if link in list_links:
                    print('Ссылка уже проверена.')
                    continue

                else:
                    list_links.append(link)

                status = await check_irecommend(service=service,
                                       link=link,
                                       pattern=df_mini_pattern,
                                       criteria=df_mini_criteria,
                                       ss_id=ss_id,
                                       project=project,
                                       driver=driver)

                if not status:
                    driver.quit()
                    driver = await get_selenium_proxy(headless=headless, proxy=proxy_on)

        if record:
            finish_sec = time.time() - start_time
            datas = {'service_name': project_irecommend,
                    'count': len_irec,
                    'date': record_date,
                    'time': finish_sec}

            print('datas', datas)
            await write_log_sheet(service, ss_id, 'logs', datas)

    if driver:
        driver.quit()

async def main_starter():
    main_irecommend_task = asyncio.create_task(main_irecommend())
    find_and_click_task = asyncio.create_task(clicker_autoit_w())

    try:
        # Ждем завершения main_irecommend_task с таймаутом
        await asyncio.wait_for(main_irecommend_task, timeout=10800)  # таймаут 1 час
        print("main_irecommend_task завершена")

    except asyncio.TimeoutError:
        print("main_irecommend_task превысила время ожидания")
        main_irecommend_task.cancel()

    except Exception as e:
        print(f"Ошибка в main_irecommend_task: {e}")

    finally:
        # В любом случае останавливаем find_and_click_task
        if not find_and_click_task.done():
            find_and_click_task.cancel()
            try:
                await find_and_click_task
            except asyncio.CancelledError:
                print("find_and_click_task остановлена")



if "__main__" in __name__:
    asyncio.run(main_starter())
    #asyncio.run(main_irecommend())

    # asyncio.create_task(async_find_and_click())
    #main_irecommend_task = asyncio.create_task(main_irecommend())
    #find_and_click_task = asyncio.create_task(async_find_and_click())














# async def click_checkbox(driver):
#     # Получение скриншота
#     screenshot = driver.get_screenshot_as_png()
#     screenshot_image = cv2.imdecode(np.frombuffer(screenshot, np.uint8), cv2.IMREAD_COLOR)
#
#     number_file = int(time.time())
#
#     temp_path = os.path.join(corn_folder, 'temp')
#     if not os.path.exists(temp_path):
#         os.makedirs(temp_path)
#         print(f"+++ Папка <{temp_path}> создана.")
#     else:
#         print(f"+++ Папка <{temp_path}> уже существует.")
#
#     file_link = os.path.join(temp_path, "image_to_find.png")
#     # driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
#     # driver.save_screenshot(file_link)
#
#     template = cv2.imread(file_link)  # Укажите путь к изображению, которое ищем
#
#     # Поиск изображения на скриншоте
#     result = cv2.matchTemplate(screenshot_image, template, cv2.TM_CCOEFF_NORMED)
#     threshold = 0.8
#     yloc, xloc = np.where(result >= threshold)
#     print(yloc, xloc)
#
#     # Если изображение найдено, кликаем по нему
#     if len(yloc) > 0 and len(xloc) > 0:
#         # Берем координаты первого совпадения
#         # Добавляем половину ширины и высоты шаблона, чтобы кликнуть в центр
#         template_height, template_width = template.shape[:2]
#         click_x = xloc[0] + template_width // 2
#         click_y = yloc[0] + template_height // 2
#
#         # Создаем объект ActionChains
#         actions = ActionChains(driver)
#
#         # Перемещаем курсор и кликаем
#         actions.move_by_offset(click_x, click_y).click().perform()
#
#         # Возвращаем курсор в начальное положение
#         actions.move_by_offset(-click_x, -click_y).perform()
#
#         print(f"Выполнен клик по координатам x={click_x}, y={click_y}")
#     else:
#         print("Элемент не найден на странице")
#
#     return driver
