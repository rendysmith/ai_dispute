import asyncio
import textwrap

from bs4 import BeautifulSoup

from utils.constants import empty_data
from utils.user_agent import get_soup

async def get_feedback(url):
    soup = await get_soup(url)
    text = soup.select_one('div.main_body').text
    clean_lines = "\n".join([line.strip() for line in text.splitlines() if line.strip()])
    return clean_lines

async def block_asn_news(link, links, min_rating, max_rating):
    soup = await get_soup(link)

    blocks = soup.select('div.comments-bl_item')
    len_b = len(blocks)
    print(f'Len B: {len_b}')

    datas = await empty_data()
    datas["Статус оценки"] = []

    for block in blocks:
        rating = int(block.select_one('div.comments-bl_item__head_mark').text)
        review_url = "https://www.asn-news.ru" + block.select_one('a.main_footer__comment-btn').get('href')

        if min_rating <= rating <= max_rating and review_url not in links:
            date = block.select_one('div.dashboard-post__date').text.strip()

            text = await get_feedback(review_url)
            author = block.select_one('div.main_head__user-name').text.strip()
            status = block.select_one('div.comments-bl_item__head_status').text.strip()

            datas['Дата'].append(date)
            datas['Текст'].append(text)
            datas['Url'].append(review_url)
            datas['Автор'].append(author)
            datas['Оценка'].append(rating)
            datas["Статус оценки"].append(status)

    return len_b, datas

if "__main__" in __name__:
    text = asyncio.run(get_feedback('https://www.asn-news.ru/rating/118177#comments'))
    print(text)




