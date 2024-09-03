import asyncio
import json
import os
import time
#import time
import numpy as np

import traceback

import warnings
#import gspread
#from oauth2client.service_account import ServiceAccountCredentials

#import gspread_dataframe as gd
#from gspread_dataframe import set_with_dataframe, get_as_dataframe
#from gs_update_utils import setup_google_sheets, upload_table_to_google_sheet
from datetime import datetime

#from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


import pandas as pd

# Получить текущую дату
current_date = datetime.now()

# Форматировать дату в виде "12.12"
formatted_date = current_date.strftime("%d.%m")

warnings.simplefilter("ignore")

abspath = os.path.dirname(os.path.abspath(__file__))
path_to_credentials = f"{abspath}/service_account.json"
print(path_to_credentials)

with open(path_to_credentials, 'r') as file:
    data = json.load(file)

print(data['client_email'])

#gc = gspread.service_account(path_to_credentials)


    # SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    # SERVICE_ACCOUNT_FILE = os.path.join(abspath, 'service_account.json')
    # credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    # service = build('sheets', 'v4', credentials=credentials).spreadsheets().values()

async def get_service():
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    SERVICE_ACCOUNT_FILE = os.path.join(abspath, 'service_account.json')
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=credentials) #.spreadsheets().values()
    return service

def create_new_range(service, SAMPLE_SPREADSHEET_ID, SAMPLE_RANGE_NAME):
    # Проверяем существование вкладки
    try:
        response = service.spreadsheets().get(spreadsheetId=SAMPLE_SPREADSHEET_ID).execute()
        sheet_exists = any(sheet['properties']['title'] == SAMPLE_RANGE_NAME for sheet in response['sheets'])
    except HttpError as e:
        print(f"An error occurred: {e}")
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
            service.spreadsheets().batchUpdate(spreadsheetId=SAMPLE_SPREADSHEET_ID, body=batch_update_body).execute()
        except HttpError as e:
            print(f"An error occurred while creating the sheet: {e}")
            return

async def append_data_to_sheet_scope(service, SAMPLE_SPREADSHEET_ID, SAMPLE_RANGE_NAME, data):
    # Подключение к Google Sheets API
    # SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    # SERVICE_ACCOUNT_FILE = os.path.join(abspath, 'service_account.json')
    # credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    # service = build('sheets', 'v4', credentials=credentials)

    create_new_range(service, SAMPLE_SPREADSHEET_ID, SAMPLE_RANGE_NAME)

    # Получаем текущие заголовки колонок
    result = service.spreadsheets().values().get(
        spreadsheetId=SAMPLE_SPREADSHEET_ID,
        range=SAMPLE_RANGE_NAME
    ).execute()

    current_columns = result.get('values', [])[0] if result.get('values', []) else []
    col_now = current_columns.copy()

    # Проверяем наличие всех ожидаемых колонок в текущих заголовках
    expected_columns = [k for k, v in data.items()]
    for column_name in expected_columns:
        if column_name not in current_columns:
            # Если колонка отсутствует, добавляем её в таблицу
            #print(column_name)
            current_columns.append(column_name)

    # Подготовка данных для записи
    values = []
    for column_name in current_columns:
        values.append(data.get(column_name, ''))  # Получаем значение из словаря или пустую строку, если ключ отсутствует

    # Запись данных в таблицу
    body = {
        'values': [values]
    }

    #input()
    if col_now != expected_columns:
        values_2 = []
        for k, v in enumerate(col_now):
            if v not in expected_columns:
                values_2.append('')

            else:
                values_2.append(values[k])

        if all(element == '' for element in values_2):
            body['values'].insert(0, expected_columns)

    result = service.spreadsheets().values().append(
        spreadsheetId=SAMPLE_SPREADSHEET_ID,
        range=SAMPLE_RANGE_NAME,
        valueInputOption='RAW',
        insertDataOption='INSERT_ROWS',  # Вставляем данные в новые строки
        body=body
    ).execute()

    print('{0} cells appended.'.format(result.get('updates').get('updatedCells')))
    return 'OK!'


# async def main():
#     url = "mail.ru"
#     url_answer = "ССылка на почту"
#     url_answer = f'''=ГИПЕРССЫЛКА("{url}"; "{url_answer}")'''
#     data = {'Link': url_answer}
#     service = await get_service()
#     await append_data_to_sheet_scope(service, '1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w', 'Паритет', data)
# asyncio.run(main())

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
    #print(values)

    if not values:
        raise ValueError("No data found in the specified range.")

    #df = pd.DataFrame(values[1:], columns=values[0])  # Assuming headers in the first row
    #print(df)

    n = 0
    VE = None

    while n <= 10:
        try:
            # Create a pandas DataFrame from the retrieved values
            df = pd.DataFrame(values[1:], columns=values[0])  # Assuming headers in the first row
            #print(df)
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

#
# def append_data_to_sheet_scope_old(SAMPLE_SPREADSHEET_ID, SAMPLE_RANGE_NAME, data):
#     # Подключение к Google Sheets API
#     SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
#     SERVICE_ACCOUNT_FILE = os.path.join(abspath, 'service_account.json')
#     credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
#     service = build('sheets', 'v4', credentials=credentials)
#
#     # Проверяем наличие вкладки SAMPLE_RANGE_NAME
#     try:
#         service.spreadsheets().values().get(
#             spreadsheetId=SAMPLE_SPREADSHEET_ID,
#             range=SAMPLE_RANGE_NAME
#         ).execute()
#     except HttpError as e:
#         if e.resp.status == 404:  # Вкладка не найдена
#             body = {
#                 'requests': [
#                     {
#                         'addSheet': {
#                             'properties': {
#                                 'title': SAMPLE_RANGE_NAME.split('!')[0]
#                             }
#                         }
#                     }
#                 ]
#             }
#             service.spreadsheets().batchUpdate(
#                 spreadsheetId=SAMPLE_SPREADSHEET_ID,
#                 body=body
#             ).execute()
#
#     # Получаем текущее количество строк в вкладке
#     result = service.spreadsheets().values().get(
#         spreadsheetId=SAMPLE_SPREADSHEET_ID,
#         range=SAMPLE_RANGE_NAME
#     ).execute()
#     num_rows = len(result.get('values', []))
#
#     # Запись данных в таблицу
#     body = {
#         'values': [list(data.values())]  # Преобразуем словарь данных в список значений
#     }
#     result = service.spreadsheets().values().append(
#         spreadsheetId=SAMPLE_SPREADSHEET_ID,
#         range=SAMPLE_RANGE_NAME + f'!A{num_rows + 1}',  # Начинаем запись с новой строки
#         valueInputOption='RAW',
#         insertDataOption='INSERT_ROWS',
#         body=body
#     ).execute()

#append_data_to_sheet_scope_old('1A73rT27Sa2Au5Bsb8v2u_C-ttDwJAYg_rY27CUfzdbw', 'test', [['data_to_append']])

# def show_all_available_tables():
#   """
#   Функция, которая показывает все доступные таблицы в Google Sheets.
#   """
#   current_path = os.path.dirname(os.path.abspath(__file__))
#   # Подключаемся к Google Sheets
#   service = setup_google_sheets(current_path, "service_account.json")
#
#   # Получаем список всех таблиц
#   spreadsheet_list = service.list_spreadsheet_files() #   .spreadsheets().list().execute()
#
#   print(spreadsheet_list)
#
#   # Выводим информацию о таблицах
#   for spreadsheet in spreadsheet_list:
#     print('Название:', spreadsheet['name'])

def get_all_spreadsheets():
    try:
        all_spreadsheets = gc.openall()
        print('all_spreadsheets -', all_spreadsheets)
        spreadsheet_names = [spreadsheet.title for spreadsheet in all_spreadsheets]
        #return spreadsheet_names

    except gspread.exceptions.APIError as AE:
        print('--- Проблемы с API')
        print(AE)
        #return []
        spreadsheet_names = []

    # Пример использования:
    for spreadsheet_name in spreadsheet_names:
        print('Название:', spreadsheet_name)

    print('----------------------------')
    return spreadsheet_names

def write_data(data, worksheet_name):
    df = pd.DataFrame(data)
    # Открытие таблицы по ее названию
    try:
        workfile = gc.open("results").worksheet(worksheet_name)
    except:
        workfile = gc.open("results").add_worksheet(title=worksheet_name, rows=1, cols=1)
        headers = list(df.columns)
        workfile.append_row(headers)  # Запись заголовков

    # Преобразование данных в DataFrame
    #print(data)

    #print(df)
    workfile.append_row(df.iloc[-1, :].tolist())

    #Еще как вариант
    # Получение последней строки
    # last_row = workfile.row_count
    # # Запись DataFrame в таблицу, начиная с новой строки
    # workfile.append_rows(df.values.tolist(), start_row=last_row + 1)


# def read_table_name(worktable_name, worksheet_name):
#     try:
#         workfile = gc.open(worktable_name)
#
#     except gspread.exceptions.APIError as AE:
#         print('--- Проблемы с API')
#         print(AE)
#
#     except gspread.exceptions.SpreadsheetNotFound as SNF:
#         print(f'--- Не найдена таблицы - {worktable_name}.')
#         print(SNF)
#
#     df = gd.get_as_dataframe(workfile.worksheet(worksheet_name))
#     df = df.dropna(axis=0, how="all").dropna(axis=1, how="all")
#     return df

# async def read_table_id_gc(spreadsheet_id, worksheet_name):
#     try:
#         workfile = gc.open_by_key(spreadsheet_id)
#
#     except gspread.exceptions.APIError as AE:
#         print('--- Проблемы с API')
#         print(AE)
#
#     except gspread.exceptions.SpreadsheetNotFound as SNF:
#         print(f'--- Не найдена таблица с ID - {spreadsheet_id}.')
#         print(SNF)
#
#     df = gd.get_as_dataframe(workfile.worksheet(worksheet_name))
#     df = df.dropna(axis=0, how="all") #.dropna(axis=1, how="all")
#     return df

async def read_table_id(service, spreadsheet_id, worksheet_name):
    try:
        # Получение данных из таблицы
        range_name = f'{worksheet_name}'
        result = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
        values = result.get('values', [])

        if not values:
            print(f'--- Лист {worksheet_name} пуст.')
            return pd.DataFrame()

        # Преобразование данных в DataFrame
        df = pd.DataFrame(values[1:], columns=values[0])
        df = df.dropna(axis=0, how="all")  # Удаление пустых строк

        return df

    except gspread.exceptions.APIError as AE:
        print('--- Проблемы с API')
        print(AE)
        return pd.DataFrame()

    except gspread.exceptions.SpreadsheetNotFound as SNF:
        print(f'--- Не найдена таблица с ID - {spreadsheet_id}.')
        print(SNF)
        return pd.DataFrame()

def update_data(worktable_name, worksheet_name, idx, text):
    workfile = gc.open(worktable_name)
    worksheet = workfile.worksheet(worksheet_name) #открываем вкладку

    all_values = worksheet.get_all_values()
    header_row = all_values[0] #прочитать заговок

    # Find the index of the new column or create a new column if it doesn't exist
    new_column_name = f"Answers"
    new_column_index = header_row.index(new_column_name) if new_column_name in header_row else len(header_row) + 1

    if new_column_name not in header_row:
        header_row.append(new_column_name)
        worksheet.update("A1", [header_row])  # Update the header row

    worksheet.update_cell(idx, new_column_index, text)


def write_data_old(worktable_name, worksheet_name, data):
    try:
        workfile = gc.open(worktable_name)
    except gspread.exceptions.APIError as AE:
        print('Проблемы с API')
        print(AE)
        return

    worksheet = workfile.worksheet(worksheet_name)
    try:
        existing_data = worksheet.get_all_values()
    except gspread.exceptions.APIError as AE:
        print('Проблемы с API при чтении данных')
        print(AE)
        return

    num_rows = len(existing_data)
    num_cols = len(existing_data[0]) if existing_data else 0

    new_data = [data]
    new_num_rows = num_rows + 1
    new_num_cols = len(data)

    if new_num_cols != num_cols:
        print("Ошибка: Число столбцов не соответствует ожидаемому")
        return

    try:
        worksheet.update(f'A{new_num_rows}', new_data)
        print("Данные успешно добавлены в таблицу.")
    except gspread.exceptions.APIError as AE:
        print('Проблемы с API при обновлении данных')
        print(AE)

async def append_data_to_sheet_cell(service, sheet_id, worksheet_name, column_name, row_number, data: str):
    try:
        # Подключение к Google Sheets API
        # SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        # SERVICE_ACCOUNT_FILE = os.path.join(abspath, 'service_account.json')
        # credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        # service = build('sheets', 'v4', credentials=credentials)

        # Получение заголовков таблицы
        header_range = f"{worksheet_name}!1:1"
        header_result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=header_range).execute()
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
            valueInputOption='RAW',
            body=value_range_body
        )
        response = request.execute()  # Асинхронный вызов
        return response

    except Exception as e:
        print(f"An error occurred: {e}")


async def append_data_to_sheet_cells(service, sheet_id, worksheet_name, column_names: list, row_number, datas: list):
    # SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    # SERVICE_ACCOUNT_FILE = os.path.join(abspath, 'service_account.json')
    # credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    # service = build('sheets', 'v4', credentials=credentials)

    # Получение заголовков таблицы
    header_range = f"{worksheet_name}!1:1"
    header_result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=header_range).execute()
    headers = header_result.get('values', [])[0]

    column_index = headers.index(column_names[0])
    column_letter = chr(65 + column_index)  # Преобразование индекса в букву (A, B, C и т.д.)

    value_input_option = 'RAW'
    values = [datas]

    body = {
        'values': values
    }

    range_name = f"{worksheet_name}!{column_letter}{row_number}"

    service.spreadsheets().values().update(
        spreadsheetId=sheet_id, range=range_name,
        valueInputOption=value_input_option, body=body
    ).execute()

def column_name_to_letter(column_name):
    """
    Преобразует название колонки в его буквенное определение.

    Args:
    column_name (str): Название колонки.

    Returns:
    str: Буквенное определение колонки.
    """
    letters = ""
    column_number = 0
    for letter in column_name:
        column_number = column_number * 26 + (ord(letter.upper()) - ord('A')) + 1
    while column_number > 0:
        column_number, remainder = divmod(column_number - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters

async def write_log_sheet(service, sheet_id, worksheet_name, data):
    service_name = data['service_name']
    date = data['date']

    df = await read_table_id(service, sheet_id, worksheet_name)

    index = df.index[df['service_name'] == service_name].tolist()
    print(index)

    if index == []:
        print('Logs: Не найден элемент вводим на новую строку')
        await append_data_to_sheet_scope(service, sheet_id, worksheet_name, data)

    else:
        print(f'Logs: {service_name} - есть в таблице, изменяем дату')
        idx = index[0] + 2
        await append_data_to_sheet_cell(service, sheet_id, worksheet_name, 'date', idx, date)

async def pars_url(service, SS_ID, R_N):
    try:
        df = await get_table_scope(service, SS_ID, R_N)
        links = df['Link'].to_list()
    except:
        links = []
    return links



