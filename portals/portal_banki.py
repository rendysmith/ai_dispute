import json
from utils.constants import empty_data
async def block_banki(page):
    datas = await empty_data()

    # Заполняем остальные поля пустыми строками для соблюдения длины списков
    for key in ["Кол-во отзывов", "Оценка компании до удаления", "Вероятность удаления",
                "Текст для поддержки", "Оценка компании после удаления", "Общий Url"]:
        datas.pop(key, None)

    # Добавляем ключ, если его нет в empty_data
    if "Статус оценки" not in datas:
        datas["Статус оценки"] = []

    # 1. Извлекаем JSON-LD (здесь полные тексты)
    json_ld_elements = await page.locator('script[type="application/ld+json"]').all_inner_texts()
    reviews_json = []
    for text in json_ld_elements:
        try:
            data = json.loads(text)
            if isinstance(data, list):
                for item in data:
                    if item.get('@type') == 'Review': reviews_json.append(item)
            elif isinstance(data, dict) and data.get('@type') == 'Review':
                reviews_json.append(data)
        except:
            continue

    # 2. Парсим карточки из DOM (для получения статусов и ссылок)
    review_cards = page.locator('div[data-gtm-view*="view_review_peoplerating"]')
    count = await review_cards.count()

    for i in range(count):
        card = review_cards.nth(i)

        # Ссылка на отзыв
        link_loc = card.locator('h3 a')
        review_url = ""
        if await link_loc.count() > 0:
            href = await link_loc.get_attribute('href')
            review_url = f"https://www.banki.ru{href}" if href and not href.startswith('http') else href

        # Берем данные из JSON (по индексу)
        review_data = reviews_json[i] if i < len(reviews_json) else {}

        # Дата
        date = review_data.get('datePublished', "")
        if not date:
            date_el = card.locator('div[data-test="text"].Kvwed').first
            date = await date_el.inner_text() if await date_el.count() > 0 else ""

        # Текст (Полный из JSON, если нет - из DOM)
        text_content = review_data.get('description', "")
        if not text_content:
            text_el = card.locator('div.HtmlInside__sc-16uvx9l-0').first
            text_content = await text_el.inner_text() if await text_el.count() > 0 else ""

        # Очистка текста от спецсимволов, которые могут ломать ячейки
        text_content = text_content.replace('\r', '').replace('\t', ' ')

        # Оценка
        rating = 0
        if 'reviewRating' in review_data:
            rating = int(review_data['reviewRating'].get('ratingValue', 0))

        # Статус (Парсим теги внутри карточки)
        status = "оценка проверяется"  # значение по умолчанию
        tags_text = await card.locator('div.gYcbTF').inner_text() if await card.locator(
            'div.gYcbTF').count() > 0 else ""
        tags_text = tags_text.lower()

        if 'проверен' in tags_text or 'засчитана' in tags_text:
            status = "оценка засчитана"
        elif 'отклонена' in tags_text:
            status = "оценка отклонена"

        # Наполняем словарь, превращая всё в СТРОКИ (защита от ошибки 400)
        datas["Дата"].append(str(date))
        datas["Текст"].append(str(text_content))
        datas["Url"].append(str(review_url))
        datas["Автор"].append(str(review_data.get('author', "")))
        datas["Оценка"].append(str(rating))
        datas["Статус оценки"].append(str(status))

    return datas


if "__main__" == __name__:

    link = 'https://www.banki.ru/insurance/responses/company/sberbankstrahovanie/?ysclid=lnfawtagh8707830496'









