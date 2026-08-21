import asyncio

from datetime import datetime


async def zoon_blocks(page, url, max_rating):
    """
    Playwright: открывает страницу zoon.ru, скроллит и собирает отзывы.

    :param page: playwright page
    :param url: ссылка на компанию
    :param max_rating: максимальный рейтинг отзыва (включительно)
    :return: dict с массивами {'Дата', 'Текст', 'Url', 'Автор', 'Оценка'}
    """
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=120_000)
    except Exception as ex:
        print(f'--- zoon goto error: {ex}')
        return {}

    await asyncio.sleep(5)

    print('Click: Reviews')
    try:
        tab = page.locator('a[data-id="reviews"][data-type="reviews"]')
        if await tab.count() > 0:
            await tab.first.click(timeout=5000)
            print('- Click: R1')
        else:
            tabs = page.locator('span[class="service-block-nav-item-text"]')
            if await tabs.count() > 1:
                await tabs.nth(1).click(timeout=5000)
                print('- Click: R2')
    except Exception as ex:
        print(f'--- zoon tab click error: {ex}')

    await asyncio.sleep(5)

    # Скролл + клик "Показать ещё" (аналог старой selenium-логики)
    n = 0
    while n < 10:
        await page.mouse.wheel(0, 1000)
        await asyncio.sleep(2)

        clicked = False
        try:
            btn = page.locator('a[data-uitest="show-more-comments-button"]')
            if await btn.count() > 0:
                await btn.first.click(timeout=5000)
                print('Click: M1')
                clicked = True
                await asyncio.sleep(3)
        except Exception:
            pass

        if not clicked:
            try:
                btn2 = page.locator('div[class="comments-next js-show-more-box"]')
                if await btn2.count() > 0:
                    await btn2.first.click(timeout=5000)
                    print('Click: M2')
                    clicked = True
                    await asyncio.sleep(3)
            except Exception:
                pass

        # Если кнопок "показать ещё" больше нет — все отзывы загружены
        if not clicked:
            break

        n += 1

    await asyncio.sleep(3)

    items = await page.evaluate(
        """() => {
            const blocks = document.querySelectorAll(
                'div[class="comment-item__container js-comment-container"][itemprop="review"]'
            );
            return Array.from(blocks).map(block => {
                const ratingMeta = block.querySelector('meta[itemprop="ratingValue"]');
                const dateMeta = block.querySelector('meta[itemprop="datePublished"]');
                const body = block.querySelector('div[class="comment-item__body js-comment-text"]');
                const author = block.querySelector('span[itemprop="name"]');
                return {
                    rating: ratingMeta ? ratingMeta.content : null,
                    date: dateMeta ? dateMeta.content : '',
                    feedback: body ? body.textContent.trim() : '',
                    dataId: block.getAttribute('data-id') || '',
                    author: author ? author.textContent.trim() : ''
                };
            });
        }"""
    )
    print(f'Len_b: {len(items)}')

    datas = {
        "Дата": [],
        "Текст": [],
        "Url": [],
        "Автор": [],
        "Оценка": [],
    }

    for item in items:
        if item['rating'] is None:
            continue

        rating = int(item['rating'])
        print("rating: ", rating)

        if rating > max_rating:
            continue

        try:
            dt = datetime.fromisoformat(item['date'])
            formatted_date = dt.strftime("%d.%m.%Y")
        except Exception:
            formatted_date = item['date']

        url_answer = f"{url}#comment{item['dataId']}"

        datas['Дата'].append(formatted_date)
        datas['Текст'].append(item['feedback'])
        datas['Url'].append(url_answer)
        datas['Автор'].append(item['author'])
        datas['Оценка'].append(rating)

    print(f'Len: {len(datas["Дата"])}')
    return datas
