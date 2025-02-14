import time

from utils.user_agent import ua


async def get_cookies(session, username, password):
    login_url = 'https://brandanalytics.ru/account/login_check'

    payload = {
        '_username': username,
        '_password': password,
        '_remember_me': 'on'
    }

    #async with aiohttp.ClientSession() as session:
    async with session.post(login_url, data=payload) as response:
        if response.status == 200:
            # Возвращаем куки
            cookies = session.cookie_jar.filter_cookies(login_url)
            #return {key: cookie.value for key, cookie in cookies.items()}
        else:
            raise Exception(f"Request failed with status code {response.status}")

    async with session.post(login_url, data=payload) as response:
        if response.status != 200:
            raise Exception(f"Login failed with status code {response.status}")

    # Шаг 2: Переходим на страницу, чтобы получить все cookies
    summary_url = 'https://brandanalytics.ru/summary'
    async with session.get(summary_url) as response:
        if response.status != 200:
            raise Exception(f"Failed to fetch summary page, status code {response.status}")

    # Возвращаем все cookies
    cookies = session.cookie_jar.filter_cookies('https://brandanalytics.ru')
    return {key: cookie.value for key, cookie in cookies.items()}

async def get_ids(session, cookies):
    tsf = int(time.time() - 5 * 24 * 3600)
    tst = int(time.time())

    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'DNT': '1',
        'Host':	'brandanalytics.ru',
        'Origin': 'https://brandanalytics.ru',
        'Priority': 'u=4',
        'Referer': f'https://brandanalytics.ru/report/12551940/summary?tsf={tsf}&tst={tst}',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'TE': 'trailers',
        'User-Agent': ua.firefox
    }

    url_themes = 'https://brandanalytics.ru/ajax/account_summary'
    async with session.post(url_themes, headers=headers, cookies=cookies) as response:
        print('Status:', response.status)
        if response.status == 200:
            r_json = await response.json()
            #print(r_json)

        else:
            return response.status

    reports = {v["name"]: k for k, v in r_json['activeThemes']['themes'].items()}
    return reports, headers