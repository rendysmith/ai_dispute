import asyncio

from utils.user_agent import get_soup


async def get_feedback_otzovru(url):
    soup = await get_soup(url, proxy=False)
    title = soup.find('h1', {"class": "element_name", "itemprop": "name"}).text

    text = soup.find('span', {"class": "comment description", "itemprop": "reviewBody"}).text

    try:
        advantages = soup.find('div', {"class": "advantages"}).text
    except:
        advantages = ''

    try:
        disadvantages = soup.find('div', {"class": "disadvantages"}).text
    except:
        disadvantages = ''

    feedback = f'{title}\n{text}\n{advantages}\n{disadvantages}'

    # feedback = soup.find('div', {'class': 'comment_row'}).text
    print(feedback)

    return feedback


async def blocks_otzovru(page, url):
    """
    Playwright: открывает страницу otzyvru.com и собирает блоки отзывов.

    :param page: playwright page
    :param url: ссылка на страницу со списком отзывов
    :return: список dict: {'url', 'rating', 'author', 'date'}
    """
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=120_000)
    except Exception as ex:
        print(f'--- otzyvru goto error: {ex}')
        return []

    await asyncio.sleep(5)

    blocks = await page.evaluate(
        """() => {
            const blocks = document.querySelectorAll('div[class="comment_row "]');
            return Array.from(blocks).map(block => {
                const get = (sel) => block.querySelector(sel);
                let url = '';
                const h2 = get('h2');
                const a = h2 ? h2.querySelector('a[href]') : null;
                if (a) url = a.href;
                if (!url) {
                    const a2 = get('a[href][target="_blank"]');
                    if (a2) url = a2.href;
                }
                let rating = '';
                const stats = get('div[class="comment_stats"]');
                const val = stats ? stats.querySelector('span[class="value-title"]') : null;
                if (val) rating = val.getAttribute('title') || '';
                let author = '';
                const rev = get('span[class="reviewer"][itemprop="name"]');
                if (rev) author = rev.textContent.trim();
                let date = '';
                const d = get('span[class="value-title"][title]');
                if (d) date = d.getAttribute('title') || '';
                return {url: url, rating: rating, author: author, date: date};
            });
        }"""
    )
    print(f'otzyvru: blocks = {len(blocks)}')
    return blocks or []
