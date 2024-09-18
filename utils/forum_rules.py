import asyncio

from cv2.version import headless

from utils.user_agent import get_soup, get_playwright
from utils.db_loader import add_data_to_db_by_filter

from models.mdl_tables import ForumRules

async def otzovik():
    forum_name = 'otzovik'

    url = 'https://otzovik.com/termofuse.php'
    soup = await get_soup(url)

    blocks = soup.find_all('table', {"class": "list"})
    forum_rule = blocks[0].text

    where_data = (ForumRules.forum_name == forum_name)
    value_data = {ForumRules.forum_rule: forum_rule}
    datas = ForumRules(forum_name=forum_name, forum_rule=forum_rule)
    status, detail = await add_data_to_db_by_filter(ForumRules, where_data, value_data, datas)
    print(status, detail)

async def nerab():
    forum_name = 'nerab'
    url = 'https://nerab.ru/agreement'

    playwright, browser, page = await get_playwright(url)
    await page.wait_for_load_state('load')

    forum_rules = await page.query_selector_all('ul')
    print(len(forum_rules))

    forum_rules = await page.query_selector_all('ul[class="subparagraph"]')
    print(len(forum_rules))


    for fr in forum_rules:
        print(fr.inner_text())







    await browser.close()
    await playwright.stop()





















    soup = await get_soup(url)
    print(soup)

    blocks = soup.find_all('ul', {"class": "subparagraph"})
    input(len(blocks))

    forum_rule = blocks[4].text
    input(forum_rule)

    where_data = (ForumRules.forum_name == forum_name)
    value_data = {ForumRules.forum_rule: forum_rule}
    datas = ForumRules(forum_name=forum_name, forum_rule=forum_rule)
    status, detail = await add_data_to_db_by_filter(ForumRules, where_data, value_data, datas)
    print(status, detail)



async def main_rulse():
    #await otzovik()
    await nerab()

if __name__ == '__main__':
    asyncio.run(main_rulse())


