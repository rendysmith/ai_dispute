import asyncio
import os
import time

import aiohttp

from utils.ba_conn import get_cookies, get_ids
from utils.gs_editor import read_table_id, get_service

tsf = int(time.time() - 3 * 24 * 3600)
tst = int(time.time())

username = os.environ.get("LOGIN_BA_DASHA")
password = os.environ.get("PASS_BA_DASHA")

themes = ['(SERM/ORM) T-Bank (ВЕСЬ!) SL (Обработка)',
          '(SERM/ORM) - Кошелёк SL (Обработка)',
          '(SERM/ORM) Тинькофф.Партнёры SL (Обработка)',
          ]

url_base = 'https://brandanalytics.ru/theme-data/'

'tst=1738875599&tsf=1738616400&requested%5B%5D=feed&sort=time_create&order=desc&page=1&size=50&limit=25&filter%5Bfmsgproc%5D%5Bany%5D%5B%5D=1&filter%5Bft%5D%5Bnot%5D%5B%5D=30008&filter%5Bft%5D%5Bnot%5D%5B%5D=30009&filter%5Bft%5D%5Bnot%5D%5B%5D=15&filter%5Bft%5D%5Bnot%5D%5B%5D=30029&filter%5Bft%5D%5Bnot%5D%5B%5D=30059&filter%5Bft%5D%5Bnot%5D%5B%5D=30025&filter%5Bfsource%5D%5Bnot%5D%5B%5D=21&filter%5Bfsource%5D%5Bnot%5D%5B%5D=14497&filter%5Bfsource%5D%5Bnot%5D%5B%5D=60575&filter%5Bfsource%5D%5Bnot%5D%5B%5D=583&filter%5Bfsource%5D%5Bnot%5D%5B%5D=10273&filter%5Bfsource%5D%5Bnot%5D%5B%5D=150992&filter%5Bfsource%5D%5Bnot%5D%5B%5D=60312&filter%5Bfsource%5D%5Bnot%5D%5B%5D=122919&filter%5Bfsource%5D%5Bnot%5D%5B%5D=122912&filter%5Bfsource%5D%5Bnot%5D%5B%5D=14640'


query = '?tst=1738875599&tsf=1738616400&requested%5B%5D=feed&sort=time_create&order=desc&page=1&size=100&limit=100&filter%5Bfmsgproc%5D%5Bany%5D%5B%5D=1&filter%5Bft%5D%5Bnot%5D%5B%5D=30008&filter%5Bft%5D%5Bnot%5D%5B%5D=30009&filter%5Bft%5D%5Bnot%5D%5B%5D=15&filter%5Bft%5D%5Bnot%5D%5B%5D=30029&filter%5Bft%5D%5Bnot%5D%5B%5D=30059&filter%5Bft%5D%5Bnot%5D%5B%5D=30025&filter%5Bfsource%5D%5Bnot%5D%5B%5D=21&filter%5Bfsource%5D%5Bnot%5D%5B%5D=14497&filter%5Bfsource%5D%5Bnot%5D%5B%5D=60575&filter%5Bfsource%5D%5Bnot%5D%5B%5D=583&filter%5Bfsource%5D%5Bnot%5D%5B%5D=10273&filter%5Bfsource%5D%5Bnot%5D%5B%5D=150992&filter%5Bfsource%5D%5Bnot%5D%5B%5D=60312&filter%5Bfsource%5D%5Bnot%5D%5B%5D=122919&filter%5Bfsource%5D%5Bnot%5D%5B%5D=122912&filter%5Bfsource%5D%5Bnot%5D%5B%5D=14640'
'tst=1738875599&tsf=1738616400&requested%5B%5D=feed&sort=time_create&order=desc&page=2&size=50&limit=25&filter%5Bfmsgproc%5D%5Bany%5D%5B%5D=1&filter%5Bft%5D%5Bnot%5D%5B%5D=30008&filter%5Bft%5D%5Bnot%5D%5B%5D=30009&filter%5Bft%5D%5Bnot%5D%5B%5D=15&filter%5Bft%5D%5Bnot%5D%5B%5D=30029&filter%5Bft%5D%5Bnot%5D%5B%5D=30059&filter%5Bft%5D%5Bnot%5D%5B%5D=30025&filter%5Bfsource%5D%5Bnot%5D%5B%5D=21&filter%5Bfsource%5D%5Bnot%5D%5B%5D=14497&filter%5Bfsource%5D%5Bnot%5D%5B%5D=60575&filter%5Bfsource%5D%5Bnot%5D%5B%5D=583&filter%5Bfsource%5D%5Bnot%5D%5B%5D=10273&filter%5Bfsource%5D%5Bnot%5D%5B%5D=150992&filter%5Bfsource%5D%5Bnot%5D%5B%5D=60312&filter%5Bfsource%5D%5Bnot%5D%5B%5D=122919&filter%5Bfsource%5D%5Bnot%5D%5B%5D=122912&filter%5Bfsource%5D%5Bnot%5D%5B%5D=14640'


'https://brandanalytics.ru/report/12551940/summary?tsf=1739566800&tst=1739825999&fmsgproc[any]=1&ft[not]=30008&ft[not]=30009&ft[not]=15&ft[not]=30029&ft[not]=30059&ft[not]=30025&fsource[not]=14497&fsource[not]=21&fsource[not]=583&fsource[not]=10273&fsource[not]=122919&fsource[not]=150992&fsource[not]=60312'
'https://brandanalytics.ru/theme-data/12551940/ tst=1739825999&tsf=1739566800&requested%5B%5D=feed&sort=time_create&order=desc&page=1&size=50&limit=25&filter%5Bfmsgproc%5D%5Bany%5D%5B%5D=1&filter%5Bft%5D%5Bnot%5D%5B%5D=30008&filter%5Bft%5D%5Bnot%5D%5B%5D=30009&filter%5Bft%5D%5Bnot%5D%5B%5D=15&filter%5Bft%5D%5Bnot%5D%5B%5D=30029&filter%5Bft%5D%5Bnot%5D%5B%5D=30059&filter%5Bft%5D%5Bnot%5D%5B%5D=30025&filter%5Bfsource%5D%5Bnot%5D%5B%5D=14497&filter%5Bfsource%5D%5Bnot%5D%5B%5D=21&filter%5Bfsource%5D%5Bnot%5D%5B%5D=583&filter%5Bfsource%5D%5Bnot%5D%5B%5D=10273&filter%5Bfsource%5D%5Bnot%5D%5B%5D=122919&filter%5Bfsource%5D%5Bnot%5D%5B%5D=150992&filter%5Bfsource%5D%5Bnot%5D%5B%5D=60312'


async def main():
    service = await get_service()
    df_offrep = await read_table_id(service, '1vxpafRIbjJriSsh9qzK_jk0ZTMJTRAX0jEep2mvBP4g', 'offrep')
    df_set = await read_table_id(service, '1vxpafRIbjJriSsh9qzK_jk0ZTMJTRAX0jEep2mvBP4g', 'set')

    async with aiohttp.ClientSession() as session:
        cookies = await get_cookies(session, username, password)

        for k, row in df_set.iterrows():
            link = row['link']

            link_spl = link.split('/')
            print(link_spl)

            for v in link_spl:
                if

            input()






        # id_themes, headers = await get_ids(session, cookies)
        # print(id_themes)
        #
        # page = 1
        # limit = 100
        # id_card = id_themes.get('(SERM/ORM) T-Bank (ВЕСЬ!) SL (Обработка)')
        # print(id_card)
        #
        # url = os.path.join(url_base, id_card, query)
        #
        # async with session.post(url, cookies=cookies) as response:
        #     if response.status == 200:
        #         try:
        #             r_json = await response.json()
        #
        #         except:
        #             print('error')
        #
        #     else:
        #         print('Status:', response.status)
        #
        # messages = r_json['feed']['messages']
        # print(len(messages))











if "__main__" == __name__:
    asyncio.run(main())