from utils.user_agent import get_soup


async def blocks_pravda(url):
    soup = await get_soup(url, proxy=False)
    blocks = soup.find_all('div', {'id': True, 'class': 'company-reviews-list-item'})
    return blocks
