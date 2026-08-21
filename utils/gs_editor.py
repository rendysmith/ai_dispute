import asyncio
import json
import os
import time

import warnings
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import pandas as pd

# Получить текущую дату
current_date = datetime.now()

warnings.simplefilter("ignore")

value_input_option = 'USER_ENTERED'

abspath = os.path.dirname(os.path.dirname(__file__))
path_to_credentials = os.path.join(abspath, 'utils', "service_account.json")
print('path_to_credentials:', path_to_credentials)

with open(path_to_credentials, 'r') as file:
    data = json.load(file)

print('client_email', data['client_email'])


async def get_service():
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    SERVICE_ACCOUNT_FILE = path_to_credentials
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=credentials)  # .spreadsheets().values()
    return service


async def sheets_execute(request, max_retries=3, wait_sec=60):
    for attempt in range(max_retries):
        try:
            return request.execute()
        except HttpError as e:
            if e.resp.status == 429 and attempt < max_retries - 1:
                print(f'--- Sheets 429, retry in {wait_sec}s ({attempt + 1}/{max_retries})')
                await asyncio.sleep(wait_sec)
            else:
                raise


async def create_new_range(service, SAMPLE_SPREADSHEET_ID, SAMPLE_RANGE_NAME):
    # Проверяем существование вкладки
    try:
        response = await sheets_execute(service.spreadsheets().get(spreadsheetId=SAMPLE_SPREADSHEET_ID))
        sheet_exists = any(sheet['properties']['title'] == SAMPLE_RANGE_NAME for sheet in response['sheets'])
    except HttpError as e:
        print(f"CNR An error occurred: {e}")
        return

    # Если вкладка не существует, создаем её
    if not sheet_exists:
        batch_update_body = {
            'requests': [{
                'addSheet': {
                    'properties': {
                        'title': SAMPLE_RANGE_NAME
                    }
                }
            }]
        }
        try:
            await sheets_execute(service.spreadsheets().batchUpdate(spreadsheetId=SAMPLE_SPREADSHEET_ID, body=batch_update_body))
            return True

        except HttpError as e:
            print(f"An error occurred while creating the sheet: {e}")
            return


async def get_table_scope(service, SAMPLE_SPREADSHEET_ID, SAMPLE_RANGE_NAME):
    """
    :param service:
    :param SAMPLE_SPREADSHEET_ID:
    :param SAMPLE_RANGE_NAME:
    :return:
    """

    # Retrieve values from the spreadsheet
    service = service.spreadsheets().values()
    result = service.get(spreadsheetId=SAMPLE_SPREADSHEET_ID, range=SAMPLE_RANGE_NAME).execute()
    values = result.get('values', [])
    # print(values)

    if not values:
        raise ValueError("No data found in the specified range.")

    n = 0
    VE = None

    while n <= 10:
        try:
            # Create a pandas DataFrame from the retrieved values
            df = pd.DataFrame(values[1:], columns=values[0])  # Assuming headers in the first row
            # print(df)
            return df

        except ValueError as VE:
            print('Get_table_scope ValueError VE:', VE)

            for idx, row in enumerate(values):
                row_0 = values[0]
                if len(row_0) < len(row):
                    rz_0 = abs(len(row) - len(row_0))
                    for i in range(rz_0):
                        numb = int(time.time())
                        values[0].append(f'New_Col_{numb}')
                    break

                elif len(row_0) > len(row):
                    rz_1 = abs(len(row) - len(row_0))
                    for i in range(rz_1):
                        row.append(None)

            time.sleep(5)
            n += 1

    return str(VE) if VE else "Unknown Error"


async def read_table_id(service, spreadsheet_id, worksheet_name):
    # Получение данных из таблицы
    range_name = f'{worksheet_name}'
    result = await sheets_execute(service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name))
    values = result.get('values', [])

    while True:
        try:
            if not values:
                print(f'--- Лист {worksheet_name} пуст.')
                return pd.DataFrame()

            # Преобразование данных в DataFrame
            df = pd.DataFrame(values[1:], columns=values[0])
            df = df.dropna(axis=0, how="all")  # Удаление пустых строк
            return df

        except ValueError as VE:
            print(VE)
            del values[0][-1]

        except Exception as Ex:
            print(f'!!!Error Ex: {Ex}')
            return pd.DataFrame()


async def append_data_to_sheet_scope(service, SAMPLE_SPREADSHEET_ID, SAMPLE_RANGE_NAME, data):
    await create_new_range(service, SAMPLE_SPREADSHEET_ID, SAMPLE_RANGE_NAME)

    # Получаем текущие заголовки колонок
    result = await sheets_execute(service.spreadsheets().values().get(
        spreadsheetId=SAMPLE_SPREADSHEET_ID,
        range=SAMPLE_RANGE_NAME
    ))

    current_columns = result.get('values', [])[0] if result.get('values', []) else []
    col_now = current_columns.copy()

    # Проверяем наличие всех ожидаемых колонок в текущих заголовках
    expected_columns = [k for k, v in data.items()]
    for column_name in expected_columns:
        if column_name not in current_columns:
            # Если колонка отсутствует, добавляем её в таблицу
            current_columns.append(column_name)

    # Подготовка данных для записи
    values = []
    for column_name in current_columns:
        values.append(data.get(column_name, ''))  # Получаем значение из словаря или пустую строку, если ключ отсутствует

    # Запись данных в таблицу
    body = {
        'values': [values]
    }

    if col_now != expected_columns:
        values_2 = []
        for k, v in enumerate(col_now):
            if v not in expected_columns:
                values_2.append('')

            else:
                values_2.append(values[k])

        if all(element == '' for element in values_2):
            body['values'].insert(0, expected_columns)

    result = await sheets_execute(service.spreadsheets().values().append(
        spreadsheetId=SAMPLE_SPREADSHEET_ID,
        range=SAMPLE_RANGE_NAME,
        valueInputOption=value_input_option,
        insertDataOption='INSERT_ROWS',  # Вставляем данные в новые строки
        body=body
    ))

    print('GS: {0} cells appended.'.format(result.get('updates').get('updatedCells')))
    return 'OK!'


async def append_data_to_sheet_scopes(service, SAMPLE_SPREADSHEET_ID, SAMPLE_RANGE_NAME, datas):
    # Пытаемся создать, если нет.
    await create_new_range(service, SAMPLE_SPREADSHEET_ID, SAMPLE_RANGE_NAME)

    # 1. Получаем текущие данные из таблицы
    result = service.spreadsheets().values().get(
        spreadsheetId=SAMPLE_SPREADSHEET_ID,
        range=f"{SAMPLE_RANGE_NAME}!A1:Z1"  # Читаем только первую строку
    ).execute()

    values = result.get('values', [])

    # Определяем, пустая ли таблица
    is_empty_sheet = len(values) == 0

    if not is_empty_sheet:
        current_columns = values[0]
    else:
        # Если таблица пустая, берем ключи из словаря как будущие заголовки
        current_columns = list(datas.keys())

    # 2. Проверяем, появились ли в datas новые ключи, которых нет в таблице
    expected_columns = list(datas.keys())
    for column_name in expected_columns:
        if column_name not in current_columns:
            current_columns.append(column_name)

    # 3. Подготовка строк данных
    rows_to_append = []
    # Считаем количество строк по самому длинному списку в datas
    row_count = max(len(v) for v in datas.values()) if datas.values() else 0

    for i in range(row_count):
        row = []
        for column_name in current_columns:
            val = datas.get(column_name, [])[i] if i < len(datas.get(column_name, [])) else ''
            row.append(str(val))  # Приведение к строке защищает от ошибки 400
        rows_to_append.append(row)

    # 4. Формируем финальный массив для записи
    final_values = rows_to_append

    # ЕСЛИ ТАБЛИЦА БЫЛА ПУСТАЯ — добавляем заголовки в самое начало
    if is_empty_sheet:
        final_values.insert(0, current_columns)

    body = {'values': final_values}

    # 5. Запись
    result = service.spreadsheets().values().append(
        spreadsheetId=SAMPLE_SPREADSHEET_ID,
        range=SAMPLE_RANGE_NAME,
        valueInputOption='USER_ENTERED',
        insertDataOption='INSERT_ROWS',
        body=body
    ).execute()

    print(f"GS: {result.get('updates').get('updatedCells')} cells updated/appended.")
    return 'OK!'


async def append_data_to_sheet_cell(service, sheet_id, worksheet_name, column_name, row_number, data: str):
    try:
        # Получение заголовков таблицы
        header_range = f"{worksheet_name}!1:1"
        header_result = await sheets_execute(service.spreadsheets().values().get(spreadsheetId=sheet_id, range=header_range))
        headers = header_result.get('values', [])[0]

        # Поиск индекса нужного столбца
        column_index = headers.index(column_name)
        column_letter = chr(65 + column_index)  # Преобразование индекса в букву (A, B, C и т.д.)

        range_name = f"{worksheet_name}!{column_letter}{row_number}"

        value_range_body = {
            'values': [[data]]  # Обернем данные в список для корректной передачи
        }

        # Выполнение запроса на обновление
        request = service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=range_name,
            valueInputOption=value_input_option,  # Было RAW
            body=value_range_body
        )
        response = await sheets_execute(request)
        print('GS: cells appended.')
        return response

    except Exception as e:
        print(f"ADSC An error occurred: {e}")
        return None


async def append_data_to_sheet_cells(service, sheet_id, worksheet_name, column_names: list, row_number, datas: list):
    # Получение заголовков таблицы
    header_range = f"{worksheet_name}!1:1"
    header_result = await sheets_execute(service.spreadsheets().values().get(spreadsheetId=sheet_id, range=header_range))
    headers = header_result.get('values', [])[0]

    try:
        # Если все колонки присутствуют
        column_index = headers.index(column_names[0])

    except:
        column_index = len(headers)  # Индекс для новой колонки (0-based)
        column_letter = chr(65 + column_index)  # Преобразуем в букву (A=65, B=66 и т.д.)
        range_name = f"{worksheet_name}!{column_letter}1"

        body = {
            "values": [[column_names]]
        }
        await sheets_execute(service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=range_name,
            valueInputOption="RAW",
            body=body
        ))

    column_letter = chr(65 + column_index)  # Преобразование индекса в букву (A, B, C и т.д.)

    values = [datas]

    body = {
        'values': values
    }

    range_name = f"{worksheet_name}!{column_letter}{row_number}"

    await sheets_execute(service.spreadsheets().values().update(
        spreadsheetId=sheet_id, range=range_name,
        valueInputOption=value_input_option, body=body
    ))
