MODEL_GEMINI = 'gemini-1.5-flash'

GPT_TOKEN = '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'

RESULT_SHEETS = '1A73rT27Sa2Au5Bsb8v2u_C-ttDwJAYg_rY27CUfzdbw'

TABLES_LIST = {
    'zoom': '1zk9x6rdVVGKgsKK_7jRwD4yN9sd745mzQv4jRrKbI9w',
    'Vkusvill': ['1HtUgQn3UJKbpjKHqqRqt5WSjDWKCJa0fOYLiM9UwcTw', 'reviews'],
    'OZON': ['1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8', 'OZON', 'OZON_link'],
    'RBI': ['1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8', 'RBI', 'RBI_link'],
    'Article_fun': ['1Pzr-jIsZXrtzriouheL8F0Q3DUEMAV1uqh4hwF98IqA'],
    'Article_eco': ['1Pzr-jIsZXrtzriouheL8F0Q3DUEMAV1uqh4hwF98IqA'],
    'Cordiant': ['1waN-H3ClPPuttkhD0CXM8ybJDIsAerbXJHD1j7CjayU', 'Отзывы'],
    'WineLab': ['1xAFv1aS1K9AxsCbYD-9bBGD2HKf0by4nuBL8diP12UI', 'Отзывы (отзовики)'],
    'Gloria Jeans': ['1-nJogtu91LB6FYfsmeZcpJafmeBUnaZ7YR1JwR3JIBs', 'Реакции АВ'],
    'Cordiant_react': ['1G3e-4BOuvySTdy-alPsVH9_DZ6IjF6nAhKpvO8HVH8w', 'Реагирование (АВ)'],
    'Tinkoff': ['', ''],
    'TinHR': ['', ''],
    'HoneyBunny': ['', ''],
    'PMEF': ['1isMeBJ57Q5jlgRcPogcNGwKwaoTWLxwtnpAWG0hEgoc', 'Карта реакций_2023']
}


months = {
    'янв': 1,
    'января': 1,
    'Jan': 1,
    'фев': 2,
    'февраля': 2,
    'Feb': 2,
    "мар": 3,
    "марта": 3,
    'Mar': 3,
    "апр": 4,
    "апреля": 4,
    'Apr': 4,
    "мая": 5,
    'May': 5,
    "июн": 6,
    "июня": 6,
    'Jun': 6,
    "июл": 7,
    "июля": 7,
    'Jul': 7,
    "авг": 8,
    "августа": 8,
    'Aug': 8,
    "сен": 9,
    "сентября": 9,
    'Sep': 9,
    "окт": 10,
    "октября": 10,
    'Oct': 10,
    "ноя": 11,
    "ноября": 11,
    'Nov': 11,
    "дек": 12,
    "декабря": 12,
    'Dec': 12,
}

status_codes = {
    507: "Недостаточно места для выполнения запроса. Сервер не может сохранить данные, необходимые для обработки запроса.",
    521: "Это ошибка от Cloudflare, указывающая, что он не может подключиться к исходному серверу, поскольку тот не отвечает на запросы."
}

platforms = {
    'irecommend': ['irecommend'],
    'otzovik': ['otzovik'],
    'ya_maps': ['maps']
}