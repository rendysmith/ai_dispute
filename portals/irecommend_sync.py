import os
import textwrap
import time
from datetime import datetime, timedelta

import random
import re

import pandas as pd

from dotenv import load_dotenv
from selenium.common import NoSuchWindowException
from selenium.webdriver.common.by import By

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from threading import Thread

from utils.ai_module import generate_and_white_sync
from utils.central_module import proxy_status_sync, get_local_ip_sync
from utils.constants import TABLES_LIST
from utils.user_agent import get_selenium_proxy_sync

#os.environ['TERM'] = 'xterm'

value_input_option = 'USER_ENTERED'

abspath = os.path.dirname(os.path.abspath(__file__))
path_to_credentials = f"{abspath}/service_account.json"
print(path_to_credentials)

current_date = datetime.now()
record_date = current_date.strftime("%d.%m.%Y")

corn_folder = os.path.dirname(os.path.dirname(__file__))

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)
days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))
ss_id = TABLES_LIST['zoom']

headless = False
proxy_on = False

image_path = os.path.join(corn_folder, 'temp/image_to_find.png')

def extract_main_site(url):
    match = re.match(r'(https?://[^/]+)', url)
    return match.group(0) if match else None

# def get_service():
#     SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
#     SERVICE_ACCOUNT_FILE = os.path.join(abspath, 'service_account.json')
#     credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
#     service = build('sheets', 'v4', credentials=credentials) #.spreadsheets().values()
#     return service
#
# def get_table_scope(service, SAMPLE_SPREADSHEET_ID, SAMPLE_RANGE_NAME):
#     """
#     :param service:
#     :param SAMPLE_SPREADSHEET_ID:
#     :param SAMPLE_RANGE_NAME:
#     :return:
#     """
#
#     # Retrieve values from the spreadsheet
#     service = service.spreadsheets().values()
#     result = service.get(spreadsheetId=SAMPLE_SPREADSHEET_ID, range=SAMPLE_RANGE_NAME).execute()
#     values = result.get('values', [])
#     #print(values)
#
#     if not values:
#         raise ValueError("No data found in the specified range.")
#
#     #df = pd.DataFrame(values[1:], columns=values[0])  # Assuming headers in the first row
#     #print(df)
#
#     n = 0
#     VE = None
#
#     while n <= 10:
#         try:
#             # Create a pandas DataFrame from the retrieved values
#             df = pd.DataFrame(values[1:], columns=values[0])  # Assuming headers in the first row
#             #print(df)
#             return df
#
#         except ValueError as VE:
#             print('Get_table_scope ValueError VE:', VE)
#
#             for idx, row in enumerate(values):
#                 row_0 = values[0]
#                 if len(row_0) < len(row):
#                     rz_0 = abs(len(row) - len(row_0))
#                     for i in range(rz_0):
#                         numb = int(time.time())
#                         values[0].append(f'New_Col_{numb}')
#                     break
#
#                 elif len(row_0) > len(row):
#                     rz_1 = abs(len(row) - len(row_0))
#                     for i in range(rz_1):
#                         row.append(None)
#
#             time.sleep(5)
#             n += 1
#
#     return str(VE) if VE else "Unknown Error"
#
# def pars_url(service, SS_ID, R_N):
#     try:
#         df = get_table_scope(service, SS_ID, R_N)
#         links = df['Link'].to_list()
#     except:
#         links = []
#     return links
#
# def create_new_range(service, SAMPLE_SPREADSHEET_ID, SAMPLE_RANGE_NAME):
#     # Проверяем существование вкладки
#     try:
#         response = service.spreadsheets().get(spreadsheetId=SAMPLE_SPREADSHEET_ID).execute()
#         sheet_exists = any(sheet['properties']['title'] == SAMPLE_RANGE_NAME for sheet in response['sheets'])
#     except HttpError as e:
#         print(f"CNR An error occurred: {e}")
#         return
#
#     # Если вкладка не существует, создаем её
#     if not sheet_exists:
#         batch_update_body = {
#             'requests': [{
#                 'addSheet': {
#                     'properties': {
#                         'title': SAMPLE_RANGE_NAME
#                     }
#                 }
#             }]
#         }
#         try:
#             service.spreadsheets().batchUpdate(spreadsheetId=SAMPLE_SPREADSHEET_ID, body=batch_update_body).execute()
#         except HttpError as e:
#             print(f"An error occurred while creating the sheet: {e}")
#             return
#
# def append_data_to_sheet_scope(service, SAMPLE_SPREADSHEET_ID, SAMPLE_RANGE_NAME, data):
#     create_new_range(service, SAMPLE_SPREADSHEET_ID, SAMPLE_RANGE_NAME)
#
#     # Получаем текущие заголовки колонок
#     result = service.spreadsheets().values().get(
#         spreadsheetId=SAMPLE_SPREADSHEET_ID,
#         range=SAMPLE_RANGE_NAME
#     ).execute()
#
#     current_columns = result.get('values', [])[0] if result.get('values', []) else []
#     col_now = current_columns.copy()
#
#     # Проверяем наличие всех ожидаемых колонок в текущих заголовках
#     expected_columns = [k for k, v in data.items()]
#     for column_name in expected_columns:
#         if column_name not in current_columns:
#             # Если колонка отсутствует, добавляем её в таблицу
#             #print(column_name)
#             current_columns.append(column_name)
#
#     # Подготовка данных для записи
#     values = []
#     for column_name in current_columns:
#         values.append(data.get(column_name, ''))  # Получаем значение из словаря или пустую строку, если ключ отсутствует
#
#     # Запись данных в таблицу
#     body = {
#         'values': [values]
#     }
#
#     #input()
#     if col_now != expected_columns:
#         values_2 = []
#         for k, v in enumerate(col_now):
#             if v not in expected_columns:
#                 values_2.append('')
#
#             else:
#                 values_2.append(values[k])
#
#         if all(element == '' for element in values_2):
#             body['values'].insert(0, expected_columns)
#
#     result = service.spreadsheets().values().append(
#         spreadsheetId=SAMPLE_SPREADSHEET_ID,
#         range=SAMPLE_RANGE_NAME,
#         valueInputOption=value_input_option,
#         insertDataOption='INSERT_ROWS',  # Вставляем данные в новые строки
#         body=body
#     ).execute()
#
#     print('GS: {0} cells appended.'.format(result.get('updates').get('updatedCells')))
#     return 'OK!'
#
# def append_data_to_sheet_cell(service, sheet_id, worksheet_name, column_name, row_number, data: str):
#     try:
#         # Получение заголовков таблицы
#         header_range = f"{worksheet_name}!1:1"
#         header_result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=header_range).execute()
#         headers = header_result.get('values', [])[0]
#
#         # Поиск индекса нужного столбца
#         column_index = headers.index(column_name)
#         column_letter = chr(65 + column_index)  # Преобразование индекса в букву (A, B, C и т.д.)
#
#         range_name = f"{worksheet_name}!{column_letter}{row_number}"
#
#         value_range_body = {
#             'values': [[data]]  # Обернем данные в список для корректной передачи
#         }
#
#         # Выполнение запроса на обновление
#         request = service.spreadsheets().values().update(
#             spreadsheetId=sheet_id,
#             range=range_name,
#             valueInputOption=value_input_option,    #Было RAW
#             body=value_range_body
#         )
#         response = request.execute()  # Асинхронный вызов
#         return response
#
#     except Exception as e:
#         print(f"ADSC An error occurred: {e}")
#         return None
#
# def append_data_to_sheet_cells(service, sheet_id, worksheet_name, column_names: list, row_number, datas: list):
#     # Получение заголовков таблицы
#     header_range = f"{worksheet_name}!1:1"
#     header_result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=header_range).execute()
#     headers = header_result.get('values', [])[0]
#
#     column_index = headers.index(column_names[0])
#     column_letter = chr(65 + column_index)  # Преобразование индекса в букву (A, B, C и т.д.)
#
#     values = [datas]
#
#     body = {
#         'values': values
#     }
#
#     range_name = f"{worksheet_name}!{column_letter}{row_number}"
#
#     service.spreadsheets().values().update(
#         spreadsheetId=sheet_id, range=range_name,
#         valueInputOption=value_input_option, body=body
#     ).execute()
#
# def write_log_sheet(service, sheet_id, worksheet_name, datas):
#     df = get_table_scope(service, sheet_id, worksheet_name)
#     service_name = datas['service_name']
#     index = df.index[df['service_name'] == service_name].tolist()
#     print(index)
#
#     if index == []:
#         print('Logs: Не найден элемент вводим на новую строку')
#         append_data_to_sheet_scope(service, sheet_id, worksheet_name, datas)
#
#     else:
#         print(f'Logs: {service_name} - есть в таблице, изменяем дату')
#         idx = index[0] + 2
#         columns = list(datas.keys())
#         values = list(datas.values())
#         append_data_to_sheet_cells(service, sheet_id, worksheet_name, columns, idx, values)

def clicker_pyautogui():
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

        time.sleep(5)

def clicker_pyscreeze():
    import pyscreeze
    #import pyautogui

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

def check_irecommend(service, link, pattern, criteria, ss_id, project, driver):
    print(f'\nLink: {link}')
    driver.get(link)

    ts = random.randint(5, max_sec)
    print(f'Wait {ts} sec...')
    time.sleep(ts) #Время ожидания
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
                time.sleep(5)
                n += 1

                if n == 10:
                    return None

        datas = {'project': project,
                 'url': link,
                 'top_url': top_url}

        #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        append_data_to_sheet_scope(service, ss_id, 'unique_url', datas)
        print('-- Record TOP link')

        driver.get(top_url)
        ts = random.randint(5, max_sec)
        print(f'Wait {ts} sec...')
        time.sleep(ts)  #Время ожидания # Время ожидания

    else:
        print('- Это уже TOP страница.')

    print('- Get Blocks')
    n = 0
    len_b = 0
    while n < 10:
        try:
            print('- Search blocks')
            #WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-type="1"]')))
            driver.execute_script("window.scrollBy(0, 500);")  # Скроллит вниз на 500 пикселей
            print('- 1')
            blocks = driver.find_elements(By.CSS_SELECTOR, 'div[data-type="1"]')
            print('- 2')
            len_b = len(blocks)
            print('Len_b =', len_b)
            break

        except:
            #driver.refresh()
            time.sleep(5)
            n += 1

    if len_b == 0:
        print('Len_b =', len_b)
        return

    links = pars_url(service, ss_id, project)
    domen = extract_main_site(link)

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

        generate_and_white_sync(service=service,
                                 url_answer=url_answer,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)

    return 'OK!'

def main_irecommend():
    # th = Thread(target=clicker_pyscreeze, args=())
    # th.start()

    proxy_active = proxy_status_sync()
    print(f'+ Proxy status: {proxy_active}')

    driver = None
    if proxy_active == 'Active':
        driver = get_selenium_proxy_sync(headless=headless, proxy=proxy_on)

    local_ip = get_local_ip_sync()
    print('local_ip', local_ip)

    service = get_service()
    df = get_table_scope(service, ss_id, 'zoom')
    #print(df)
    idx_num_row = df.index[df['Проект'] == 'Кол-во строк'].tolist()[0]
    print(idx_num_row)
    df_counts = pd.Series(df.iloc[idx_num_row].values, index=df.columns).reset_index()
    df_counts[0] = pd.to_numeric(df_counts[0], errors='coerce')
    # Удаляем строки с NaN значениями в указанной колонке
    df_counts = df_counts.dropna(subset=[0])
    df_counts = df_counts.sort_values(by=0)
    #print(df_counts)

    list_ = df_counts['index'].to_list()
    print(list_)
    #random.shuffle(list_)

    df_uniq = get_table_scope(service, ss_id, 'unique_url')

    df_logs = get_table_scope(service, ss_id, 'logs')
    print(df_logs)

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
                append_data_to_sheet_cell(service, ss_id, 'logs', 'status', idx_logs + 2, f'Proxy {proxy_active}')
                break

            else:
                append_data_to_sheet_cell(service, ss_id, 'logs', 'status', idx_logs + 2,
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
                f'\n*************************{idx}*({left})*{project}**************************\n----------------- {link} ----------------')

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

                status = check_irecommend(service=service,
                                       link=link,
                                       pattern=df_mini_pattern,
                                       criteria=df_mini_criteria,
                                       ss_id=ss_id,
                                       project=project,
                                       driver=driver)

                if not status:
                    driver.quit()
                    driver = get_selenium_proxy_sync(headless=headless, proxy=proxy_on)

        if record:
            finish_sec = time.time() - start_time
            datas = {'service_name': project_irecommend,
                    'count': len_irec,
                    'date': record_date,
                    'time': finish_sec}

            print('datas', datas)
            write_log_sheet(service, ss_id, 'logs', datas)

    if driver:
        driver.quit()

if "__main__" in __name__:
    main_irecommend()













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
