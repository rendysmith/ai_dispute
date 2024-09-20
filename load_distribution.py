import asyncio

import numpy as np
import pandas as pd

from models.mdl_tables import HostsZoom
from utils.constants import TABLES_LIST
from utils.db_loader import read_data_from_db
from utils.gs_editor import get_table_scope, get_service, append_data_to_sheet_cell

ss_id = TABLES_LIST['zoom']
tab_name = 'logs'

async def load_distribution(service):
    status, results = await read_data_from_db(HostsZoom, 1, 1)

    hosts = [result.host for result in results]
    #hosts = ['85.192.49.227', '85.192.49.224']
    print(hosts)

    hosts_number = len(hosts)
    print(hosts_number)

    df_logs = await get_table_scope(service, ss_id, tab_name)
    df_sorted = df_logs.sort_values(by='count')
    print(df_sorted)

    df = df_sorted
    df['assigned_service'] = np.tile(hosts, len(df) // hosts_number + 1)[:len(df)]
    print(df)

    for idx, row in df.iterrows():
        hst = row['assigned_service']
        print(idx, hst)
        await append_data_to_sheet_cell(service, ss_id, tab_name, 'reserve', idx+2, hst)
        await asyncio.sleep(3)









async def main_distribution():
    service = await get_service()
    await load_distribution(service)




if "__main__" in __name__:
    asyncio.run(main_distribution())

