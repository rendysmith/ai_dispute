import asyncio

from utils.central_module import get_local_ip
from utils.gs_editor import get_service
from utils.user_agent import get_soup, get_selenium_proxy

local_ip = asyncio.run(get_local_ip())
if '176.124.192' in local_ip:
    headless = True
    proxy_on = True
    only_text = False

else:
    print(f'local_ip: {local_ip}')
    headless = False
    proxy_on = False
    only_text = False

async def blocks_ok(url):
    soup = await get_soup(url, proxy=proxy_on)
    blocks = soup.find_all('div', {'class': 'comments_i __new-comments h-mod'})
    print(len(blocks))
    return blocks


async def check_ok(service, url, pattern, criteria, ss_id, project, driver):
    blocks = await blocks_ok(url)

    for block in blocks:
        continue







async def main_ok():
    service = await get_service()

    url = 'http://www.ok.ru/profile/547913323727/statuses/157921667567823'
    url = 'https://ok.ru/akunyagerrero.pedro/statuses/157799286296783'

    driver = await get_selenium_proxy(url, headless=headless, proxy=proxy_on)
    await check_ok(service, url, 1, 1, "1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w", "AlphaPet", driver)

if __name__ == '__main__':
    asyncio.run(main_ok())