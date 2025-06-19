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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException


from utils.ai_module import generate_and_white
from utils.central_module import wait_for_portal, proxy_status, get_local_ip, get_hpo
from utils.constants import TABLES_LIST
from utils.gs_editor import append_data_to_sheet_scope, pars_url, get_service, get_table_scope, \
    append_data_to_sheet_cell, write_log_sheet
from utils.proxy_bridge import get_one_proxy
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

#local_ip = asyncio.run(get_local_ip())
int_time = int(time.time())

box_black = os.path.join(corn_folder, 'temp', 'box_black.png')
box_white = os.path.join(corn_folder, 'temp', 'box_white.png')

screenshot_path = os.path.join(corn_folder, "temp", f"{int_time}_screen.png")
result_after_click = os.path.join(corn_folder, "temp", "result_after_click.png")
detected_checkboxes = os.path.join(corn_folder, 'temp', "detected_checkboxes.png")

headless, proxy_on, only_text = asyncio.run(get_hpo())
headless = False
print("-- HPO:", headless, proxy_on)

recorded = 0

async def click_checkbox(driver):
    n = 0
    while n < 20:
        try:
            iframe_locator = driver.find_element(By.XPATH, "//iframe[contains(@title, 'challenge') or contains(@name, 'cf-chl-widget')]")
            WebDriverWait(driver, 20).until(
                EC.frame_to_be_available_and_switch_to_it(iframe_locator)
            )
            print("Switched to Cloudflare iframe.")

            click_box = driver.find_element(By.CSS_SELECTOR, 'input[type="checkbox"]')
            checkbox_element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(click_box)
            )
            print("Checkbox element found.")
            checkbox_element.click()

            print("Checkbox clicked successfully.")
            driver.switch_to.default_content()
            print("Switched back to default content.")

            #click_box.click()
            return driver

        except:
            await asyncio.sleep(2)
            print('------------NO Checkbox--------------')
            print(driver.page_source)
            n+=1

    return driver

async def clicker_pyautogui():
    import pyautogui
    from PIL import Image
    # Загрузка изображения искомого элемента

    while True:
        try:
            # Считываем изображение, которое нужно найти
            target_image = Image.open(image_path)

            # Ищем все вхождения изображения на экране
            locations = pyautogui.locateAllOnScreen(target_image)

            for location in locations:
                # Получаем координаты центра найденного изображения
                center = pyautogui.center(location)

                # Кликаем по центру найденного элемента
                pyautogui.click(center)
                print(f"---> Clicked on {center}")
                break

        except:
            print("-- Элемент не найден. 2")

        await asyncio.sleep(5)

async def clicker_pywinauto_old():
    """
    Only for Windows
    pip3 install pywinauto
    pip3 install Pillow
    Returns:

    """
    import pywinauto
    from pywinauto.application import Application
    from PIL import Image
    import numpy as np

    while True:
        print('---- Click checkbox pywinauto')
        try:
            # Подключаемся к уже открытому Chrome
            app = Application(backend="uia").connect(title_re=".*Chrome.*", timeout=10)  # timeout added for robustness
            window = app.window(title_re=".*Chrome.*")

            # Преобразуем PNG-изображение в совместимый с pywinauto формат
            image = Image.open(image_path)
            image = np.array(image)  # Convert to NumPy array

            # Ищем элемент на экране по изображению
            wrapper = window.wait_for_element(timeout=10, control_type="Pane",
                                              found_index=0)  # Added timeout and assumed first Pane

            rect = wrapper.rectangle()
            x, y = rect.left, rect.top
            width, height = rect.width(), rect.height()

            # Search within the specified wrapper
            coords = pywinauto.controls.win32_controls.HwndWrapper._perform_image_recognition(
                wrapper.element_info, image
            )

            # Получаем координаты центра элемента
            click_x = x + coords[0] + image.shape[1] // 2
            click_y = y + coords[1] + image.shape[0] // 2

            # Выполняем клик по центру элемента
            window.click_input(coords=(click_x, click_y))
            print('---> Clock! ')

        except pywinauto.findbestmatch.MatchError:
            raise Exception(f"--- Изображение '{image_path}' не найдено на экране.")

        except Exception as e:
            raise Exception(f"--- Произошла ошибка: {e}")

        finally:
            await asyncio.sleep(5)

async def clicker_pywinauto():
    import pywinauto
    from pywinauto.application import Application
    # ... (остальная часть функции до try)
    while True:
        print('---- Click checkbox pywinauto')
        try:
            app = Application(backend="uia").connect(title_re=".*Chrome.*", timeout=10)
            window = app.window(title_re=".*Chrome.*")

            # --- ИСПРАВЛЕНИЕ: Найдем элемент, используя его реальные свойства ---
            try:
                # Используем свойства Name и ControlType, которые вы нашли в Accessibility Insights
                verify_checkbox_element = window.child_window(
                    control_type="CheckBox",
                    title="Verify you are human"
                )

                # Дожидаемся, пока элемент станет готовым (например, видимым и активным)
                wrapper = verify_checkbox_element.wait('ready', timeout=10)

            # Перехватываем конкретное исключение, если элемент не найден
            except pywinauto.findbestmatch.MatchError:
                 print("--- Не удалось найти чекбокс 'Verify you are human' по указанным свойствам.")
                 await asyncio.sleep(5)
                 continue # Пропускаем клик и переходим к следующей итерации

            # --- Клик по найденному элементу ---
            # Теперь 'wrapper' - это обертка вашего чекбокса. Кликаем по нему.
            wrapper.click_input()

            # На скриншоте также видно, что элемент поддерживает Patterns: InvokePattern и TogglePattern.
            # Теоретически, вместо click_input() можно попробовать использовать эти паттерны:
            # wrapper.toggle() # Для переключения состояния (отмечено/не отмечено)
            # wrapper.invoke() # Для выполнения действия по умолчанию (обычно эквивалентно клику)
            # Но click_input() на обертке элемента часто самый простой и надежный способ.


            print('---> Click! ') # Исправлено "Clock!" на "Click!"
            return

        except Exception as e:
            print(f"--- Произошла ошибка в процессе работы: {e}")

        finally:
            await asyncio.sleep(5)

async def clicker_pyscreeze():
    """
    Ищет заданное изображение на экране и кликает по его центру.

    Args:
        image_path (str): Путь к файлу с изображением, которое нужно найти.
        confidence (float): Уровень уверенности для поиска (от 0.0 до 1.0).
                            Более низкое значение менее строго, но может привести к ложным срабатываниям.
                            Требуется установка opencv-python.
        grayscale (bool): Искать в оттенках серого. Может ускорить поиск и сделать его
                          более устойчивым к незначительным изменениям цвета. Требуется opencv-python.
        duration (float): Длительность движения мыши до клика в секундах.

    Returns:
        bool: True, если изображение найдено и клик выполнен, False в противном случае.
    """

    import pyscreeze
    import pyautogui  # Импортируем pyautogui для управления мышью
    import time

    confidence = 0.7
    grayscale = True
    #confidence=0.9
    #grayscale=False
    duration=0.2

    for image_path in [box_white, box_black]:
        print(f"Ищем изображение: {image_path} на экране...")

        try:
            # Ищем центр изображения на экране с помощью pyscreeze
            location = pyscreeze.locateCenterOnScreen(
                image_path,
                confidence=confidence,
                grayscale=grayscale
            )

            if location:
                x, y = location
                print(f"Изображение найдено по координатам: ({x}, {y}). Выполняем клик.")

                # Перемещаем курсор и кликаем с помощью pyautogui
                # Добавим небольшую задержку и плавность движения
                pyautogui.moveTo(x, y, duration=duration)  # Исправлено на pyautogui.moveTo
                time.sleep(0.1)  # Короткая пауза перед кликом
                pyautogui.click(x, y)  # Исправлено на pyautogui.click
                print(f"Клик {image_path} выполнен.")
                return True

            else:
                print("Изображение не найдено на экране.")
                if image_path == box_black:
                    return False

        except pyscreeze.ImageNotFoundException:
            # Это исключение возникает, если locateCenterOnScreen не находит изображение
            print("Изображение не найдено на экране (исключение ImageNotFoundException).")
            if image_path == box_black:
                return False

        except Exception as e:
            print(f"Произошла ошибка при поиске или клике: {e}")
            if image_path == box_black:
                return False

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

    n = 0
    while n < 10:
        try:
            # Поиск изображения
            if auto.pixel_search(image_path):
                x, y = auto.mouse_get_pos()
                auto.mouse_click("left", x, y)
                print('--- Click checkbox')

            else:
                print('--- NO checkbox')

            n += 1
            print(f'-- autoit {n}')
            await asyncio.sleep(5)

        except:
            n += 1
            print(f'-- autoit {n}')
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

async def find_and_click_cloudflare_checkbox(driver):
    import cv2
    import pyautogui

    # Сделаем скриншот экрана

    pyautogui.screenshot(screenshot_path)

    def find_checkbox_and_click():
        # Загружаем изображение
        screen = cv2.imread(screenshot_path)

        # Конвертируем в оттенки серого
        gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)

        # Метод 1: Поиск квадратного чекбокса
        # Применяем пороговую обработку для выделения контрастных областей
        _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

        # Ищем контуры
        contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # Ищем квадратные контуры подходящего размера
        checkbox_candidates = []
        for contour in contours:
            # Аппроксимируем контур
            approx = cv2.approxPolyDP(contour, 0.01 * cv2.arcLength(contour, True), True)

            # Проверяем, похож ли контур на квадрат (4 точки) и имеет подходящий размер
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = float(w) / h

            # Если контур почти квадратный и подходящего размера (от 15x15 до 50x50 пикселей)
            if len(approx) >= 4 and 0.8 <= aspect_ratio <= 1.2 and 15 <= w <= 50 and 15 <= h <= 50:
                area = cv2.contourArea(contour)
                if area > 200:  # Минимальная площадь, чтобы исключить шум
                    checkbox_candidates.append((x, y, w, h))
                    # Рисуем найденный контур для отладки
                    cv2.rectangle(screen, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Метод 2: Попытка поиска текста "Verify you are human" и определение положения рядом
        # Этот метод требует использования библиотеки для OCR, например, pytesseract
        # Здесь мы просто проверим найденные кандидаты относительно центра экрана,
        # предполагая, что капча обычно находится в центре

        # Сортируем кандидатов по близости к центру экрана
        height, width = screen.shape[:2]
        center_x, center_y = width // 2, height // 2

        checkbox_candidates.sort(key=lambda rect:
        ((rect[0] + rect[2] / 2 - center_x) ** 2 +
         (rect[1] + rect[3] / 2 - center_y) ** 2))

        # Сохраняем изображение с выделенными кандидатами для отладки
        cv2.imwrite(detected_checkboxes, screen)

        # Если нашли кандидатов, кликаем по центру первого (самого вероятного)
        if checkbox_candidates:
            best_candidate = checkbox_candidates[0]
            x, y, w, h = best_candidate

            # Вычисляем центр чекбокса
            center_x = x + w // 2
            center_y = y + h // 2

            print(f"Найден возможный чекбокс по координатам: ({center_x}, {center_y})")

            # Делаем движение мышью плавным и человекоподобным
            current_x, current_y = pyautogui.position()
            pyautogui.moveTo(center_x, center_y, duration=0.5)  # Плавное движение к чекбоксу
            time.sleep(0.2)  # Небольшая пауза перед кликом
            pyautogui.click()  # Клик по чекбоксу
            time.sleep(0.5)  # Пауза после клика

            return True
        else:
            print("Не удалось найти подходящие чекбоксы на изображении")
            return False

    # Метод 3: Поиск по шаблону
    def find_by_template():
        # Необходимо иметь заранее сохраненное изображение чекбокса
        # template_path = "cloudflare_checkbox_template.png"

        # Проверяем, есть ли шаблонное изображение
        template_path = image_path
        if not os.path.exists(template_path):
            print(f"Шаблон {template_path} не найден. Сначала нужно создать шаблонное изображение чекбокса.")
            return False

        # Загружаем шаблон и скриншот
        template = cv2.imread(template_path, 0)
        screen = cv2.imread(screenshot_path, 0)

        # Находим совпадения шаблона на изображении
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        # Если совпадение достаточно хорошее
        if max_val > 0.7:  # Порог совпадения (от 0 до 1)
            # Получаем координаты
            h, w = template.shape
            top_left = max_loc
            center_x = top_left[0] + w // 2
            center_y = top_left[1] + h // 2

            print(f"Найдено совпадение с шаблоном по координатам: ({center_x}, {center_y})")

            # Делаем движение мышью плавным и человекоподобным
            pyautogui.moveTo(center_x, center_y, duration=0.5)
            time.sleep(0.2)
            pyautogui.click()
            time.sleep(0.5)

            return True
        else:
            print("Шаблон не найден на изображении")
            return False

    # Выполняем поиск и клик
    try:
        # Пробуем сначала метод определения по контурам
        if find_checkbox_and_click():
            print("Клик по чекбоксу выполнен методом определения контуров")
        # Если не сработало, пробуем метод по шаблону
        elif find_by_template():
            print("Клик по чекбоксу выполнен методом поиска по шаблону")
        else:
            print("Не удалось найти и кликнуть по чекбоксу. Пробуем универсальный способ...")

            # Универсальный способ - клик в центр области, где чаще всего находится капча
            screen_width, screen_height = pyautogui.size()

            # Предполагаем, что капча находится в центральной области экрана
            center_x = screen_width // 2
            center_y = screen_height // 2

            # Смещаемся немного вверх от центра, где обычно находится чекбокс
            click_y = center_y - 50

            print(f"Пробуем кликнуть по предполагаемой позиции чекбокса: ({center_x}, {click_y})")
            pyautogui.moveTo(center_x, click_y, duration=0.5)
            time.sleep(0.2)
            pyautogui.click()

        # Ждем некоторое время, чтобы страница прошла проверку и загрузилась
        print("Ожидание загрузки страницы после клика...")
        time.sleep(5)

        # Делаем снимок экрана для проверки результата
        pyautogui.screenshot(result_after_click)
        print(f"Сохранен скриншот после клика: {result_after_click}")

    except Exception as e:
        print(f"Произошла ошибка: {e}")

async def get_driver():
    driver = await get_selenium_proxy(headless=headless, proxy=proxy_on)
    #driver = await get_seleniumbase_SB(headless=False, proxy=proxy_on)
    return driver

async def check_irecommend(service, link, pattern, criteria, ss_id, project, driver):
    global recorded
    print(f'\nLink: {link}')

    try:
        driver.get(link)
        print('Driver OK')

    except:
        driver = await get_driver()
        driver.get(link)
        print('New Driver OK')

    box_true = True
    while box_true:
        await wait_for_portal()  # Время ожидания
        box_true = await clicker_pyscreeze()

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
            driver = await get_driver()
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
        url_answer = url_n
        print(url_answer)

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

        recorded += 1

    return 'OK!'

async def main_irecommend():
    proxy_active = await proxy_status()
    print(f'+ Proxy status: {proxy_active}')

    driver = None
    if proxy_active == 'Active':
        driver = await get_driver()

    local_ip = await get_local_ip()
    print('- local_ip Irec', local_ip)

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
                await append_data_to_sheet_cell(service, ss_id, 'logs', 'status',
                                                idx_logs + 2,
                                                f'Proxy {proxy_active}')
                break

            else:
                await append_data_to_sheet_cell(service, ss_id, 'logs', 'status',
                                                idx_logs + 2,
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

        global recorded
        recorded = 0

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

                if not driver:
                    #driver.quit()
                    driver = await get_driver()

        if record:
            finish_sec = time.time() - start_time
            datas = {'service_name': project_irecommend,
                    'count': len_irec,
                    'date': record_date,
                    'time': finish_sec,
                    'recorded': recorded}

            print('datas', datas)
            await write_log_sheet(service, ss_id, 'logs', datas)

    if driver:
        driver.quit()

async def main_tst():
    import scrapy
    from scrapy.crawler import CrawlerProcess

    from utils.user_agent import ua

    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    load_dotenv(dotenv_path)

    login_proxy = os.environ.get("LOGIN_PROXY")
    pass_proxy = os.environ.get("PASS_PROXY")
    url = 'https://irecommend.ru/content/detskaya-molochnaya-smes-nutricia-molochnaya-smes-nutrilon-1-dlya-detei-s-rozhdeniya-do-6-me'

    class UsersSpider(scrapy.Spider):
        name = 'users'
        start_urls = [
            url,
        ]

        custom_settings = {
            'RETRY_HTTP_CODES': [500, 503, 504, 400, 408, 521],
            'RETRY_TIMES': 5
        }

        def parse(self, response):
            if response.status == 521:
                self.logger.warning("Got 521 error, retrying...")
                return

            blocks = response.css('li.item')
            print(len(blocks))

            for item in response.css('li.item'):
                user_link = item.css('a[href^="/users/"]')
                username = user_link.css('::text').get()
                print(username)
                user_url = user_link.attrib['href']

                # if username and user_url:
                #     yield {
                #         'username': username.strip(),
                #         'profile_url': response.urljoin(user_url)
                #     }

    async def run_spider():
        host, port = await get_one_proxy()
        proxy_1 = f'http://{login_proxy}:{pass_proxy}@{host}:{port}'

        host, port = await get_one_proxy()
        proxy_2 = f'http://{login_proxy}:{pass_proxy}@{host}:{port}'

        host, port = await get_one_proxy()
        proxy_3 = f'http://{login_proxy}:{pass_proxy}@{host}:{port}'

        process = CrawlerProcess(settings={
            'USER_AGENT': ua.chrome,
            'HTTPPROXY_ENABLED': True,
            'HTTPPROXY_PROXY_LIST': [proxy_1, proxy_2, proxy_3],
            'DOWNLOAD_FAIL_ON_DATALOSS': False
        })
        process.crawl(UsersSpider)
        process.start()

    await run_spider()

async def main_starter():
    main_irecommend_task = asyncio.create_task(main_irecommend())
    #find_and_click_task_1 = asyncio.create_task(clicker_autoit_w())
    #find_and_click_task_2 = asyncio.create_task(clicker_pywinauto())

    try:
        # Ждем завершения main_irecommend_task с таймаутом
        await asyncio.wait_for(main_irecommend_task, timeout=10800)  # таймаут 1 час
        print("main_irecommend_task завершена")

    except asyncio.TimeoutError:
        print("main_irecommend_task превысила время ожидания")
        main_irecommend_task.cancel()

    except Exception as e:
        print(f"Ошибка в main_irecommend_task: {e}")

    # finally:
    #     # В любом случае останавливаем find_and_click_task
    #     if not find_and_click_task_1.done():
    #         find_and_click_task_1.cancel()
    #         find_and_click_task_2.cancel()
    #         try:
    #             await find_and_click_task_1
    #             await find_and_click_task_2
    #         except asyncio.CancelledError:
    #             print("find_and_click_task остановлена")

if "__main__" in __name__:
    asyncio.run(main_irecommend())