import asyncio
import os

import numpy as np
import requests
from dotenv import load_dotenv

from models.mdl_tables import HostsZoom
from utils.constants import TABLES_LIST
from utils.db_loader import read_data_from_db
from utils.gs_editor import get_table_scope, get_service, append_data_to_sheet_cell, read_table_id

ss_id = TABLES_LIST['zoom']
tab_name = 'logs'

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

token_proxy = os.environ.get("TOKEN_PROXY")
id_proxy = os.environ.get("ID_PROXY")
login_proxy = os.environ.get("LOGIN_PROXY")
pass_proxy = os.environ.get("PASS_PROXY")

async def get_api_service():
    url = f'https://api.proxy5.net/api/service/{id_proxy}'
    headers = {
        'Authorization': f'Basic {token_proxy}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    response = requests.get(url, headers=headers)
    print(response)
    r_json = response.json()
    print(r_json)
    return r_json


async def change_ip(ip):
    url = f'https://proxy5.net/api/getproxy/?action=setip&login={login_proxy}&{pass_proxy}=LbLYF35E&ip={ip}'
    r = requests.get(url)
    status_code = r.status_code
    if status_code != 200:
        print(status_code, r.text)

    else:
        print(status_code, r.text)

async def load_distribution(service):
    status, results = await read_data_from_db(HostsZoom, 100, 1)

    hosts = [result.host for result in results]
    #hosts = ['85.192.49.227', '85.192.49.224']
    print(hosts)

    hosts_number = len(hosts)
    print(hosts_number)

    df_logs = await get_table_scope(service, ss_id, tab_name)
    print(df_logs)
    df_sorted = df_logs.sort_values(by='count')
    print(df_sorted)

    df = df_sorted
    df['assigned_service'] = np.tile(hosts, len(df) // hosts_number + 1)[:len(df)]
    print(df)

    service_data = await get_api_service()

    for idx, row in df.iterrows():
        hst = row['assigned_service']

        if service_data['status'] != 'Active':
            hst = 'status = Deactive'

        print(idx, hst)
        await append_data_to_sheet_cell(service, ss_id, tab_name, 'reserve', idx+2, hst)
        await asyncio.sleep(3)

    bindedip = service_data['bindedip']
    if bindedip not in hosts:
        await change_ip(hosts[0])

async def main_distribution():
    service = await get_service()
    await load_distribution(service)

if "__main__" in __name__:
    #asyncio.run(())
    # ip = '176.124.192.164'
    # asyncio.run(change_ip(ip))
    asyncio.run(main_distribution())

