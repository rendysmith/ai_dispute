import asyncio

from utils.user_agent import get_soup
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











async def main_rulse():
    await otzovik()


if __name__ == '__main__':
    asyncio.run(main_rulse())


