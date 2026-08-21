import re


async def extract_review_text(block):
    """
    Извлекает текст отзыва из HTML-блока и возвращает его в формате:
    Что нравится?
    <текст>
    Что можно улучшить?
    <текст>
    """
    lines = []

    # 1. Извлекаем "Что нравится?"
    pros_title = block.find('div', class_='review__title', string=re.compile(r'Что нравится', re.IGNORECASE))
    if pros_title:
        pros_text = pros_title.find_next_sibling('div', class_='review__text')
        if pros_text:
            lines.append("Что нравится?")
            lines.append(pros_text.get_text(separator='\n', strip=True))

    # 2. Извлекаем "Что можно улучшить?"
    cons_title = block.find('div', class_='review__title', string=re.compile(r'Что можно улучшить', re.IGNORECASE))
    if cons_title:
        cons_text = cons_title.find_next_sibling('div', class_='review__text')
        if cons_text:
            lines.append("Что можно улучшить?")
            lines.append(cons_text.get_text(separator='\n', strip=True))

    # Собираем всё в единую строку с переносами строк
    if lines:
        return '\n'.join(lines) + '\n'

    return ""
