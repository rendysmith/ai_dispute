import asyncio

from utils.constants import months


def _parse_ru_date(date_string):
    """
    Парсит дату tripadvisor вида 'Опубликовано 25 августа 2024 г.' в dd.mm.yyyy.
    Не зависит от локали системы.
    """
    cleaned = date_string.replace('Опубликовано ', '').replace(' г.', '').strip()
    parts = cleaned.split()
    if len(parts) == 3:
        day = parts[0].zfill(2)
        month = str(months.get(parts[1].lower(), '00')).zfill(2)
        year = parts[2]
        if month != '00' and day.isdigit() and year.isdigit():
            return f"{day}.{month}.{year}"
    return ''


async def blocks_tripadvisor(page, url):
    """
    Playwright: собирает отзывы tripadvisor.ru со страницы отзывов.

    :param page: playwright page
    :param url: ссылка на страницу отзывов
    :return: список dict: {'formatted_date', 'author', 'feedback', 'url_answer', 'rating'}
    """
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=120_000)
    except Exception as ex:
        print(f'--- tripadvisor goto error: {ex}')
        return []

    await asyncio.sleep(5)

    items = await page.evaluate(
        """() => {
            const blocks = document.querySelectorAll('div[data-automation="tab"]');
            const result = [];
            const CLASS_A = 'a[class="BMQDV _F Gv wSSLS SwZTJ FGwzt ukgoS"]';
            blocks.forEach(block => {
                try {
                    const links = block.querySelectorAll(CLASS_A);
                    if (links.length < 2) return;

                    const texts = block.querySelectorAll('span.yCeTE');
                    if (texts.length < 2) return;

                    const urlAnswer = links[1].href || '';
                    const feedback = texts[0].textContent.trim() + '\\n' + texts[1].textContent.trim();

                    const dateEl = block.querySelector("div[class='biGQs _P VImYz ncFvv navcl']");
                    const dateString = dateEl ? dateEl.textContent.trim() : '';

                    const author = links[0] ? links[0].textContent.trim() : '';

                    const rating = block.querySelectorAll(
                        'path[d="M 12 0C5.388 0 0 5.388 0 12s5.388 12 12 12 12-5.38 12-12c0-6.612-5.38-12-12-12z"]'
                    ).length;

                    result.push({dateString, feedback, author, urlAnswer, rating});
                } catch (e) {}
            });
            return result;
        }"""
    )

    datas = []
    for item in items or []:
        datas.append({
            "formatted_date": _parse_ru_date(item.get('dateString', '')),
            "author": item.get('author', ''),
            "feedback": item.get('feedback', ''),
            "url_answer": item.get('urlAnswer', ''),
            "rating": item.get('rating', 0),
        })

    print(f'tripadvisor: blocks = {len(datas)}')
    return datas
