import asyncio
import requests

from utils.user_agent import get_soup, get_data_without_proxy


async def blocks_pikabu(link):
    #r = requests.get(link)
    soup = await get_data_without_proxy(link, text_format=False)
    print(soup)
    print(type(soup))


    blocks = soup.find_all('div', {'class': 'comment', 'data-indent': '0'})
    input(len(blocks))



    url = 'https://pikabu.ru/ajax/comments_actions.php'

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Csrf-Token": "709dc6558eeb462b193fa28d868ef2ad",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://pikabu.ru",
        "Referer": "https://pikabu.ru/story/korporativnyiy_chellendzh_dobra_12082740",
        "DNT": "1",
        "Connection": "keep-alive",
        "Cookie": "__ddgid_=4PdZBhNtfokYTu10; __ddg1_=UBhJAkpcEVn6SrCrKJm2; pcid=wKYoQv4vnv2; ..."
    }

    payload = {
        "action": "get_comments_by_ids",
        "ids": "191517555,191517881,191517647,249343914,211591942,209137588,191517551,191517411,191517597"
    }

    # Выполняем POST-запрос
    response = requests.post(url, headers=headers, data=payload)

    # Проверяем статус и выводим результат
    if response.status_code == 200:
        print(response.json())  # Если ответ в формате JSON
    else:
        print(f"Ошибка: {response.status_code}")


async def main_pikabu():
    link = 'https://pikabu.ru/story/10_luchshikh_torrentobmennikov_v_rossii_aktivnyikh_v_2021_7995137#comments'
    await blocks_pikabu(link)

if "__main__" in __name__:
     asyncio.run(main_pikabu())




