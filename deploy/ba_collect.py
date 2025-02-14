import asyncio
import os
import time

import aiohttp

from utils.ba_conn import get_cookies, get_ids

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

async def main():
    async with aiohttp.ClientSession() as session:
        cookies = await get_cookies(session, username, password)
        id_themes, headers = await get_ids(session, cookies)
        print(id_themes)

        page = 1
        limit = 100
        id_card = id_themes.get('(SERM/ORM) T-Bank (ВЕСЬ!) SL (Обработка)')
        print(id_card)

        url = os.path.join(url_base, id_card, query)

        async with session.post(url, cookies=cookies) as response:
            if response.status == 200:
                try:
                    r_json = await response.json()

                except:
                    print('error')

            else:
                print('Status:', response.status)

        messages = r_json['feed']['messages']
        print(len(messages))











if "__main__" == __name__:
    asyncio.run(main())