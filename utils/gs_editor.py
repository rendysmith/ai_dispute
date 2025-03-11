import asyncio
import json
import os
import time
#import time
#import numpy as np
#import traceback

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
from sqlalchemy.util import await_only

# Получить текущую дату
current_date = datetime.now()

# Форматировать дату в виде "12.12"
formatted_date = current_date.strftime("%d.%m")

warnings.simplefilter("ignore")

value_input_option = 'USER_ENTERED'


#project_root = os.path.dirname(os.path.dirname(__file__))

abspath = os.path.dirname(os.path.dirname(__file__))
path_to_credentials = os.path.join(abspath, 'utils', "service_account.json")
print('path_to_credentials:', path_to_credentials)

with open(path_to_credentials, 'r') as file:
    data = json.load(file)

print('client_email', data['client_email'])

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

async def get_service():
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    #SERVICE_ACCOUNT_FILE = os.path.join(abspath, 'service_account.json')
    SERVICE_ACCOUNT_FILE = path_to_credentials
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=credentials) #.spreadsheets().values()
    return service

async def create_new_range(service, SAMPLE_SPREADSHEET_ID, SAMPLE_RANGE_NAME):
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

async def read_table_id(service, spreadsheet_id, worksheet_name):
    # Получение данных из таблицы
    range_name = f'{worksheet_name}'
    result = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
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
    # Подключение к Google Sheets API
    # SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    # SERVICE_ACCOUNT_FILE = os.path.join(abspath, 'service_account.json')
    # credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    # service = build('sheets', 'v4', credentials=credentials)

    await create_new_range(service, SAMPLE_SPREADSHEET_ID, SAMPLE_RANGE_NAME)

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
        valueInputOption=value_input_option,
        insertDataOption='INSERT_ROWS',  # Вставляем данные в новые строки
        body=body
    ).execute()

    print('GS: {0} cells appended.'.format(result.get('updates').get('updatedCells')))
    return 'OK!'

async def append_data_to_sheet_scopes(service, SAMPLE_SPREADSHEET_ID, SAMPLE_RANGE_NAME, datas):
    status = await create_new_range(service, SAMPLE_SPREADSHEET_ID, SAMPLE_RANGE_NAME)

    # Получаем текущие заголовки колонок
    result = service.spreadsheets().values().get(
        spreadsheetId=SAMPLE_SPREADSHEET_ID,
        range=SAMPLE_RANGE_NAME
    ).execute()

    current_columns = result.get('values', [])[0] if result.get('values', []) else []

    # Проверяем наличие всех ожидаемых колонок
    expected_columns = list(datas.keys())
    for column_name in expected_columns:
        if column_name not in current_columns:
            current_columns.append(column_name)

    # Подготовка данных для записи в формате списка строк
    rows_to_append = []
    row_count = max(len(v) for v in datas.values())  # Определяем количество строк по длине самого длинного списка
    for i in range(row_count):
        row = []
        for column_name in current_columns:
            # Получаем значение из списка или пустую строку, если индекс выходит за пределы
            row.append(datas.get(column_name, [])[i] if i < len(datas.get(column_name, [])) else '')
        rows_to_append.append(row)

    # Запись данных в таблицу
    body = {
        'values': rows_to_append
    }

    if status:
        headers = [k for k in datas.keys()]
        body['values'].insert(0, headers)

    result = service.spreadsheets().values().append(
        spreadsheetId=SAMPLE_SPREADSHEET_ID,
        range=SAMPLE_RANGE_NAME,
        valueInputOption='USER_ENTERED',  # Можно изменить на 'RAW' при необходимости
        insertDataOption='INSERT_ROWS',  # Вставляем данные в новые строки
        body=body
    ).execute()

    print('GS: {0} cells appended.'.format(result.get('updates').get('updatedCells')))
    return 'OK!'

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
            valueInputOption=value_input_option,    #Было RAW
            body=value_range_body
        )
        response = request.execute()  # Асинхронный вызов
        return response

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

async def append_data_to_sheet_cells(service, sheet_id, worksheet_name, column_names: list, row_number, datas: list):
    # Получение заголовков таблицы
    header_range = f"{worksheet_name}!1:1"
    header_result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=header_range).execute()
    headers = header_result.get('values', [])[0]

    try:
        #Если все колонки присутствуют
        column_index = headers.index(column_names[0])

    except:
        column_index = len(headers)  # Индекс для новой колонки (0-based)
        column_letter = chr(65 + column_index)  # Преобразуем в букву (A=65, B=66 и т.д.)
        range_name = f"{worksheet_name}!{column_letter}1"

        body = {
            "values": [[column_names]]
        }
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=range_name,
            valueInputOption="RAW",
            body=body
        ).execute()

    column_letter = chr(65 + column_index)  # Преобразование индекса в букву (A, B, C и т.д.)

    values = [datas]

    body = {
        'values': values
    }

    range_name = f"{worksheet_name}!{column_letter}{row_number}"

    service.spreadsheets().values().update(
        spreadsheetId=sheet_id, range=range_name,
        valueInputOption=value_input_option, body=body
    ).execute()

async def write_log_sheet(service, sheet_id, worksheet_name, datas):
    df = await read_table_id(service, sheet_id, worksheet_name)
    service_name = datas['service_name']
    index = df.index[df['service_name'] == service_name].tolist()
    #print(index)

    if index == []:
        print('Logs: Не найден элемент вводим на новую строку')
        await append_data_to_sheet_scope(service, sheet_id, worksheet_name, datas)

    else:
        print(f'Logs: {service_name} - есть в таблице, изменяем дату')
        idx = index[0] + 2
        columns = list(datas.keys())
        values = list(datas.values())
        await append_data_to_sheet_cells(service, sheet_id, worksheet_name, columns, idx, values)

async def pars_url(service, SS_ID, R_N):
    try:
        df = await get_table_scope(service, SS_ID, R_N)
        links = df['Link'].to_list()
    except:
        links = []
    return links

async def get_all_sheet_names(service, spreadsheet_id):
    """
    Получение названий всех листов в таблице
    :param service: авторизованный сервис Google Sheets
    :param spreadsheet_id: ID Google таблицы
    :return: список названий листов
    """
    # Получение информации о таблице
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    # Извлечение названий листов
    sheet_names = [sheet['properties']['title'] for sheet in spreadsheet['sheets']]
    return sheet_names

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

async def main():
    service = await get_service()
    # current_date = datetime.now().strftime("%d.%m.%Y")
    # data = {'service_name': "СберСтрахование_2", 'count': 5, 'date': current_date}
    # ss_id = '1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w'
    # await write_log_sheet(service, ss_id, 'logs', data)

    df = await read_table_id(service, '1uAgMSukxmO0KZLZ-C5mhv7c3IsxvgyD1vxaSPg3TykU', 'ORM (test)')
    print(df)

if "__main__" == __name__:
    asyncio.run(main())




