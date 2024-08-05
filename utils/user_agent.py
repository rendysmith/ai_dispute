import asyncio

from fake_useragent import UserAgent

ua = UserAgent()

async def gen_ua(url):
    headers = {
        'User-Agent': ua.chrome,
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': url}

    return headers
#
# a = asyncio.run(gen_ua('mail.ru'))
# print(a)