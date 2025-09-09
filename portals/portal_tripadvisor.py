
from datetime import datetime

import asyncio

import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
import re
import json

from utils.user_agent import clean_html, get_selenium_proxy


async def extract_reviews_bs4(text_content):
    """
    Извлекает данные об отзывах из текста с использованием BeautifulSoup.
    Ищет фрагменты JSON, содержащие данные отзывов, и парсит их.

    Args:
        text_content (str): Строка, содержащая HTML/текст с данными отзывов.

    Returns:
        list: Список списков, где каждый внутренний список содержит словари
              с данными об отзывах в формате:
              [{'author': 'Имя', 'feedback': 'Текст', 'date': 'YYYY-MM-DD', 'url': 'ссылка'}, ...]
    """
    # BeautifulSoup используется для извлечения скриптового контента или поиска по тегам,
    # но в данном случае проще искать JSON напрямую в строке.
    # Тем не менее, создадим объект BeautifulSoup для потенциального будущего использования.
    #soup = BeautifulSoup(text_content, 'html.parser')

    reviews_data = []

    # Поиск всех потенциальных JSON-объектов WebPresentation_ReviewCardWeb в тексте
    # Это регулярное выражение ищет начало структуры, характерной для отзывов
    pattern = r'\{\"__typename\":\"WebPresentation_ReviewCardWeb\".*?\}'
    matches = re.findall(pattern, text_content)

    if not matches:
        # Альтернативный способ: попробовать найти более крупные блоки данных
        # и обработать их как JSON, если они содержат нужную информацию
        # (Это может быть неэффективно для больших файлов)
        print("Не найдены явные блоки WebPresentation_ReviewCardWeb. Попытка парсинга всего содержимого.")
        # В этом случае можно было бы искать в soup, но проще продолжить работу со строкой.
        # Разделим текст на более крупные части и попробуем найти нужные данные.
        # Однако для предоставленного фрагмента первый способ должен сработать.

    current_review_block = []
    collected_reviews = []

    for i, match in enumerate(matches):
        try:
            # Попытка загрузить JSON
            json_obj = json.loads(match)
            current_review_block.append(json_obj)

            # Предположим, что каждый отзыв - это отдельный блок WebPresentation_ReviewCardWeb.
            # Мы можем обрабатывать их по одному.
            # Извлечение данных из одного JSON-объекта
            review_info = {}

            # Имя автора
            user_profile = json_obj.get('userProfile', {})
            localized_name = user_profile.get('localizedDisplayName', {})
            author = localized_name.get('text', 'Неизвестный автор')
            review_info['author'] = author

            # Текст отзыва
            html_text = json_obj.get('htmlText', {})
            feedback = html_text.get('text', 'Текст отзыва отсутствует')
            # Убираем HTML-теги, если они есть (BeautifulSoup может помочь, но для простоты используем regex)
            feedback_clean = re.sub(r'<[^>]+>', '', feedback) if feedback else ''
            review_info['feedback'] = feedback_clean

            # Дата публикации
            raw_date = json_obj.get('rawPublishedDate', '')
            review_info['date'] = raw_date

            # URL
            card_link = json_obj.get('cardLink', {})
            web_route = card_link.get('webRoute', {})
            url = web_route.get('webLinkUrl', '')
            review_info['url'] = url

            # Добавляем собранный отзыв в список
            if any(review_info.values()): # Проверяем, что хотя бы одно поле заполнено
                collected_reviews.append(review_info)

        except json.JSONDecodeError:
            # Если не удалось декодировать JSON, пропускаем этот фрагмент
            print(f"Ошибка декодирования JSON в совпадении {i}: {match[:100]}...")
            continue

    # Формируем итоговый список в нужном формате
    # Внешний список содержит один внутренний список со всеми найденными отзывами
    reviews_data.append(collected_reviews)

    return reviews_data

async def blocks_tripadvisor_sel(driver, url):
    import locale
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')


    input('Проставьте фильтры->')

    await asyncio.sleep(5)

    blocks = driver.find_elements(By.CSS_SELECTOR, 'div[data-automation="tab"]')
    print("Len_B:", len(blocks))


    datas = []

    for k, block in enumerate(blocks):
        print(f'********************{k}**************************')

        try:
            url_answer = block.find_elements(By.CSS_SELECTOR, 'a[class="BMQDV _F Gv wSSLS SwZTJ FGwzt ukgoS"]')[1].get_attribute('href')
        except:
            continue

        #print("url_answer", url_answer)

        texts = block.find_elements(By.CSS_SELECTOR, 'span.yCeTE')

        if len(texts) < 2:
            continue

        feedback = f'{texts[0].text}\n{texts[1].text}'
        #print('+++', feedback)
        #htmlText = await clean_html(block.find_element(By.CSS_SELECTOR, 'span.yCeTE').text )
        #feedback = f'{htmlTitle}\n{htmlText}'

        date_string = block.find_element(By.CSS_SELECTOR, "div[class='biGQs _P VImYz ncFvv navcl']").text
        #print('***', date_string)
        cleaned_string = date_string.replace('Опубликовано ', '').replace(' г.', '').strip()
        date_obj = datetime.strptime(cleaned_string, '%d %B %Y')

        #date_obj = datetime.strptime(date_string, "%Y-%m-%d")
        date_formating = date_obj.strftime("%d.%m.%Y")

        author = block.find_element(By.CSS_SELECTOR, 'a[class="BMQDV _F Gv wSSLS SwZTJ FGwzt ukgoS"]').text

        ratings_path = block.find_elements(By.CSS_SELECTOR, 'path[d="M 12 0C5.388 0 0 5.388 0 12s5.388 12 12 12 12-5.38 12-12c0-6.612-5.38-12-12-12z"]')
        rating = len(ratings_path)
        print(f'rating: {rating}')

        datas.append({
            "formatted_date": date_formating,
            "author": author,
            "feedback": feedback,
            "url_answer": url_answer,
            'rating': rating
        })

    return datas






async def blocks_tripadvisor(url, page):
    url = 'https://www.tripadvisor.ru/data/graphql/ids'

    offset = f'r{str((page-1)*10)}'

    headers = {
        "Host": "www.tripadvisor.ru",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:141.0) Gecko/20100101 Firefox/141.0",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": f"https://www.tripadvisor.ru/Attraction_Review-g298484-d8514577-Reviews-o{offset}-Moskvarium-Moscow_Central_Russia.html",
        "content-type": "application/json",
        "Origin": "https://www.tripadvisor.ru",
        "DNT": "1",
        "Connection": "keep-alive",
        "Cookie": "TAUnique=%1%enc%3AnyQAadspGLX5qFlfHQYWYKpK96%2FEHeH69ziQ0jjJhFVnire%2FeLCVLVJ5uuGrqSjFNox8JbUSTxk%3D; TASameSite=1; datadome=N3bctdHDiXo1Q_IjZy5v1BsbEppxS~9t19VWIz71OJ5YBeSkWYeuc1GjsF4pAjeagO7xjxcORB4j_w4qh7kzBo6YPS~Hahn8qf2YSbQTMSn7j1XY7szduZAi2v0BuQ40; OptanonConsent=isGpcEnabled=0&datestamp=Mon+Sep+08+2025+09%3A36%3A34+GMT%2B0300+(%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0%2C+%D1%81%D1%82%D0%B0%D0%BD%D0%B4%D0%B0%D1%80%D1%82%D0%BD%D0%BE%D0%B5+%D0%B2%D1%80%D0%B5%D0%BC%D1%8F)&version=202405.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=26cb4067-c506-4912-bd45-619e22d7cb50&interactionCount=1&isAnonUser=1&landingPath=https%3A%2F%2Fwww.tripadvisor.ru%2FAttraction_Review-g298484-d8514577-Reviews-Moskvarium-Moscow_Central_Russia.html&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A0; TATrkConsent=eyJvdXQiOiJBRFYsU09DSUFMX01FRElBIiwiaW4iOiJBTkEsRlVOQ1RJT05BTCJ9; __vt=MMZj8wbqznywsBnUABQCT24E-H_BQo6gx1APGQJPtzf_2w7FkXdGH1utV3ZN20de1eD3618UlZ6qWBtx5MC6iVC5YphyRI03FcTvD-Cej5MnCbgJBInOMGdLnIkv8cYrz-9vr3Ed5t6bmfKRg8B8d9ah9ys; TADCID=kQ-PjBYAm1sNoIApABQCJ4S5rDsRRMescG99HippfogiEfbWaOOt6N6tTURl_WlLiXcjh0yqGZ9BWq6LV2dm8RLvs52nm9oiNvA; TASSK=enc%3AAKT01958ndrOR%2FzDW9%2FJarDLkdo%2FAy%2BP21pQHruBON4gTzF1VZiEQCi11vJt%2ByOudQwfLffGAT%2BcsCYgiXLoUwKRrO4Kj4inH9Y4kjOvIyNNdrSSkf6md5gDJ5Sb%2Fg2pkg%3D%3D; TASession=V2ID.32D0003DE6394205A8747463E9690F90*SQ.1*LS.UpdateSessionDatesAjax*HS.recommended*ES.popularity*DS.5*SAS.popularity*FPS.oldFirst*FA.1*DF.0*TRA.true; PAC=AF9SP7-d0mENP5WrgzLu5A6nvnPWB9wQEXmLqp51hSz2ktte7T7KGUi1toau1fCM9CNmfQC5hNqH_OdFKBVmPKBgMk11_xSpbR86cmCr7_onWZ8iApKTnqoSe2EBzyi426oGqJ97zlJJm4skjTor0jZhDSSvDTvBZtaQ6saubT1bnO5hLKKnW0S0rz-WWeUT21gIYwqG6GQifpbkD_jUG4yeetrzrGyMopMNI-qBjDBzdIsKarMmJbE8GOt-ucuKwXURts8laNQdh-lPPSqehGU%3D; ServerPool=C; PMC=V2*MS.65*MD.20250908*LD.20250908; TART=%1%enc%3AoqofBTRe0iW0eEZSwmQ3YhpJDF5eH6AZbalZOpgRE4iCuB6g%2BD%2BiOkL4bsjQOoGdJCOjqmidnvw%3D; TATravelInfo=V2*A.2*MG.-1*HP.2*FL.3*RS.1; CM=%1%mds%2C1757310992771%2C1757397392%7C; TAUD=ARC-1757310992769*RDD-1-2025_09_08; TASID=05FDF73BE5E8711A94F2C250C56CE78A",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "same-origin",
        "Sec-Fetch-Site": "same-origin",
        "Priority": "u=4",
        "TE": "trailers"
    }


    #url = f'https://www.tripadvisor.ru/Attraction_Review-g298484-d8514577-Reviews-o{offset}-Moskvarium-Moscow_Central_Russia.html'
    #print(url)

    print(offset)
    #parameters = {"variables":{"request":{"tracking":{"screenName":"Attraction_Review","pageviewUid":"23088aff-0298-4c6c-a418-37e5b1bf9984"},"routeParameters":{"contentType":"attraction","contentId":"8514577"},"clientState":{"userInput":[{"inputKey":"rating","inputValues":["1","2","3"]},{"inputKey":"months","inputValues":[]},{"inputKey":"type","inputValues":[]}]},"updateToken":None},"commerce":{},"sessionId":"6541D1A4960C9870F5F3BD7D1474A8AE","tracking":{"screenName":"Attraction_Review","pageviewUid":"23088aff-0298-4c6c-a418-37e5b1bf9984"},"currency":"RUB","currentGeoPoint":None,"unitLength":"KILOMETERS"},"extensions":{"preRegisteredQueryId":"45c77754ff77a0e7"}}
    #parameters = {"variables":{"page":"Attraction_Review","pos":"ru-RU","parameters":[{"key":"geoId","value":"298484"},{"key":"detailId","value":"8514577"},{"key":"offset","value":"r10"}],"factors":["TITLE","META_DESCRIPTION","MASTHEAD_H1","MAIN_H1","IS_INDEXABLE","RELCANONICAL"],"route":{"page":"Attraction_Review","params":{"geoId":298484,"detailId":8514577,"offset":"r10"}},"currencyCode":"RUB"},"extensions":{"preRegisteredQueryId":"18d4572907af4ea5"}},{"variables":{"pageName":"Attraction_Review","relativeUrl":"/Attraction_Review-g298484-d8514577-Reviews-or10-Moskvarium-Moscow_Central_Russia.html","parameters":[{"key":"geoId","value":"298484"},{"key":"detailId","value":"8514577"},{"key":"offset","value":"r10"}],"route":{"page":"Attraction_Review","params":{"geoId":298484,"detailId":8514577,"offset":"r10"}},"routingLinkBuilding":True},"extensions":{"preRegisteredQueryId":"211573a2b002568c"}},{"variables":{"request":{"tracking":{"screenName":"Attraction_Review","pageviewUid":"23088aff-0298-4c6c-a418-37e5b1bf9984"},"routeParameters":{"contentType":"attraction","contentId":"8514577"},"clientState":{"userInput":[{"inputKey":"rating","inputValues":["1","2","3"]},{"inputKey":"months","inputValues":[]},{"inputKey":"type","inputValues":[]}]},"updateToken":"eyJ2ZXIiOiJ2MiIsInR5cCI6IkpXVCIsImFsZyI6IkVTMjU2IiwidmVyc2lvbiI6IjEifQ.eyJvYmplY3QiOiJ7XCJAY1wiOlwiLlBhZ2luZ1VwZGF0ZVRva2VuXCIsXCJjbHVzdGVySWRzXCI6W1wiUE9JX1JFVklFV1NfV0VCXCJdLFwicHJvdmlkZXJVcGRhdGVUb2tlbnNcIjp7XCJUUkFOU0xBVEVfUkVWSUVXU1wiOntcIkBjXCI6XCJjb20udHJpcGFkdmlzb3Iuc2VydmljZS5hcHMuYWRhcHRlcnMuaG90ZWxzLlRyYW5zbGF0ZVJldmlld3NUb2tlblwiLFwic2hvdWxkVHJhbnNsYXRlXCI6dHJ1ZSxcInJldmlld0lkc1wiOlsxMDI4MjUxMTM0LDEwMjIyNjE5NDEsMTAxMTQxNTkwNCwxMDA2ODgwODIxLDEwMDU5OTM1MjIsMTAwNTc0NjIwNSw5OTQxNzIzODksOTkxNzM4ODg5LDk4ODYxMTkwMSw5ODgzNzQ2MDNdLFwidG90YWxDb3VudFwiOjU0NSxcInNob3dUcmFuc2xhdGVIZWFkZXJcIjpmYWxzZSxcImZhdm9yaXRlUmV2aWV3SWRcIjpudWxsfSxcIldFQl9SRVZJRVdTX0ZJTFRFUlwiOntcIkBjXCI6XCJjb20udHJpcGFkdmlzb3Iuc2VydmljZS5hcHMud2Vic2FuZGJveC5tb2RlbC5yZXZpZXdzYW5kcWEuV2ViUmV2aWV3c0ZpbHRlclRva2VuXCIsXCJzZWxlY3RlZEZpbHRlcnNcIjp7XCJSQVRJTkdcIjpbXCIxXCIsXCIyXCIsXCIzXCJdLFwiVFlQRVwiOltdLFwiTU9OVEhTXCI6W119fX0sXCJwYWdlSW5kZXhcIjoxMCxcInR5cGVcIjpcIlBBR0lOQVRJT05cIixcInBvbGxpbmdTZXF1ZW5jZU51bVwiOjB9In0.MzJlMjUwMzMtNTIyNi00NmRkLThmNTQtNGMxYjNlMzMwNjhmLk1FWUNJUUROTFNkSllOMWhUOFFWU2JqM2JyTUlUWklONUlTWXNrWUFHUnNmTUpSN1pnSWhBSktMMHpVV3N3dFFrbjQwaHN4anhFQ2JiMzRMOVlhdTZ4X1dqWktOdnpUZQ"},"commerce":{},"sessionId":"6541D1A4960C9870F5F3BD7D1474A8AE","tracking":{"screenName":"Attraction_Review","pageviewUid":"23088aff-0298-4c6c-a418-37e5b1bf9984"},"currency":"RUB","currentGeoPoint":None,"unitLength":"KILOMETERS"},"extensions":{"preRegisteredQueryId":"45c77754ff77a0e7"}},{"variables":{"page":"Attraction_Review","params":[{"key":"geoId","value":"298484"},{"key":"detailId","value":"8514577"},{"key":"offset","value":"r10"}],"route":{"page":"Attraction_Review","params":{"geoId":298484,"detailId":8514577,"offset":"r10"}}},"extensions":{"preRegisteredQueryId":"f742095592a84542"}}
    #parameters = {"variables":{"page":"Attraction_Review","pos":"ru-RU","parameters":[{"key":"geoId","value":"298484"},{"key":"detailId","value":"8514577"},{"key":"offset","value":offset}],"factors":["TITLE","META_DESCRIPTION","MASTHEAD_H1","MAIN_H1","IS_INDEXABLE","RELCANONICAL"],"route":{"page":"Attraction_Review","params":{"geoId":298484,"detailId":8514577,"offset":offset}},"currencyCode":"RUB"},"extensions":{"preRegisteredQueryId":"18d4572907af4ea5"}},{"variables":{"pageName":"Attraction_Review","relativeUrl":f"/Attraction_Review-g298484-d8514577-Reviews-o{offset}-Moskvarium-Moscow_Central_Russia.html","parameters":[{"key":"geoId","value":"298484"},{"key":"detailId","value":"8514577"},{"key":"offset","value":offset}],"route":{"page":"Attraction_Review","params":{"geoId":298484,"detailId":8514577,"offset":offset}},"routingLinkBuilding":True},"extensions":{"preRegisteredQueryId":"211573a2b002568c"}},{"variables":{"request":{"tracking":{"screenName":"Attraction_Review","pageviewUid":"23088aff-0298-4c6c-a418-37e5b1bf9984"},"routeParameters":{"contentType":"attraction","contentId":"8514577"},"clientState":{"userInput":[{"inputKey":"rating","inputValues":["1","2","3"]},{"inputKey":"months","inputValues":[]},{"inputKey":"type","inputValues":[]}]},"updateToken":"eyJ2ZXIiOiJ2MiIsInR5cCI6IkpXVCIsImFsZyI6IkVTMjU2IiwidmVyc2lvbiI6IjEifQ.eyJvYmplY3QiOiJ7XCJAY1wiOlwiLlBhZ2luZ1VwZGF0ZVRva2VuXCIsXCJjbHVzdGVySWRzXCI6W1wiUE9JX1JFVklFV1NfV0VCXCJdLFwicHJvdmlkZXJVcGRhdGVUb2tlbnNcIjp7XCJUUkFOU0xBVEVfUkVWSUVXU1wiOntcIkBjXCI6XCJjb20udHJpcGFkdmlzb3Iuc2VydmljZS5hcHMuYWRhcHRlcnMuaG90ZWxzLlRyYW5zbGF0ZVJldmlld3NUb2tlblwiLFwic2hvdWxkVHJhbnNsYXRlXCI6dHJ1ZSxcInJldmlld0lkc1wiOlsxMDI4MjUxMTM0LDEwMjIyNjE5NDEsMTAxMTQxNTkwNCwxMDA2ODgwODIxLDEwMDU5OTM1MjIsMTAwNTc0NjIwNSw5OTQxNzIzODksOTkxNzM4ODg5LDk4ODYxMTkwMSw5ODgzNzQ2MDNdLFwidG90YWxDb3VudFwiOjU0NSxcInNob3dUcmFuc2xhdGVIZWFkZXJcIjpmYWxzZSxcImZhdm9yaXRlUmV2aWV3SWRcIjpudWxsfSxcIldFQl9SRVZJRVdTX0ZJTFRFUlwiOntcIkBjXCI6XCJjb20udHJpcGFkdmlzb3Iuc2VydmljZS5hcHMud2Vic2FuZGJveC5tb2RlbC5yZXZpZXdzYW5kcWEuV2ViUmV2aWV3c0ZpbHRlclRva2VuXCIsXCJzZWxlY3RlZEZpbHRlcnNcIjp7XCJSQVRJTkdcIjpbXCIxXCIsXCIyXCIsXCIzXCJdLFwiVFlQRVwiOltdLFwiTU9OVEhTXCI6W119fX0sXCJwYWdlSW5kZXhcIjoyMCxcInR5cGVcIjpcIlBBR0lOQVRJT05cIixcInBvbGxpbmdTZXF1ZW5jZU51bVwiOjB9In0.MzJlMjUwMzMtNTIyNi00NmRkLThmNTQtNGMxYjNlMzMwNjhmLk1FWUNJUUN1VzBSeldvTVI0Q0JTQ19pam5zR1FOQXVZdUVVeEJ5U2VGTlJ1VUhGaEJnSWhBTjVpWEtBSGZaT2xxWjY0cGVYTVFLLUM1RmtIejZXWjZLc1p6X3g0S3VDZw"},"commerce":{},"sessionId":"6541D1A4960C9870F5F3BD7D1474A8AE","tracking":{"screenName":"Attraction_Review","pageviewUid":"23088aff-0298-4c6c-a418-37e5b1bf9984"},"currency":"RUB","currentGeoPoint":None,"unitLength":"KILOMETERS"},"extensions":{"preRegisteredQueryId":"45c77754ff77a0e7"}},{"variables":{"page":"Attraction_Review","params":[{"key":"geoId","value":"298484"},{"key":"detailId","value":"8514577"},{"key":"offset","value":offset}],"route":{"page":"Attraction_Review","params":{"geoId":298484,"detailId":8514577,"offset":offset}}},"extensions":{"preRegisteredQueryId":"f742095592a84542"}}
    parameters = {"variables":{"request":{"tracking":{"screenName":"Attraction_Review","pageviewUid":"586564fd-30c1-44fc-b52a-f5b6660a47b0"},"routeParameters":{"contentType":"attraction","contentId":"8514577"},"clientState":{"userInput":[{"inputKey":"rating","inputValues":["1","2","3"]},{"inputKey":"months","inputValues":[]},{"inputKey":"type","inputValues":[]}]},"updateToken":"eyJ2ZXIiOiJ2MiIsInR5cCI6IkpXVCIsImFsZyI6IkVTMjU2IiwidmVyc2lvbiI6IjEifQ.eyJvYmplY3QiOiJ7XCJAY1wiOlwiLlBhZ2luZ1VwZGF0ZVRva2VuXCIsXCJjbHVzdGVySWRzXCI6W1wiUE9JX1JFVklFV1NfV0VCXCJdLFwicHJvdmlkZXJVcGRhdGVUb2tlbnNcIjp7XCJUUkFOU0xBVEVfUkVWSUVXU1wiOntcIkBjXCI6XCJjb20udHJpcGFkdmlzb3Iuc2VydmljZS5hcHMuYWRhcHRlcnMuaG90ZWxzLlRyYW5zbGF0ZVJldmlld3NUb2tlblwiLFwic2hvdWxkVHJhbnNsYXRlXCI6dHJ1ZSxcInJldmlld0lkc1wiOlsxMDI4MjUxMTM0LDEwMjIyNjE5NDEsMTAxMTQxNTkwNCwxMDA2ODgwODIxLDEwMDU5OTM1MjIsMTAwNTc0NjIwNSw5OTQxNzIzODksOTkxNzM4ODg5LDk4ODYxMTkwMSw5ODgzNzQ2MDNdLFwidG90YWxDb3VudFwiOjU0NSxcInNob3dUcmFuc2xhdGVIZWFkZXJcIjpmYWxzZSxcImZhdm9yaXRlUmV2aWV3SWRcIjpudWxsfSxcIldFQl9SRVZJRVdTX0ZJTFRFUlwiOntcIkBjXCI6XCJjb20udHJpcGFkdmlzb3Iuc2VydmljZS5hcHMud2Vic2FuZGJveC5tb2RlbC5yZXZpZXdzYW5kcWEuV2ViUmV2aWV3c0ZpbHRlclRva2VuXCIsXCJzZWxlY3RlZEZpbHRlcnNcIjp7XCJSQVRJTkdcIjpbXCIxXCIsXCIyXCIsXCIzXCJdLFwiVFlQRVwiOltdLFwiTU9OVEhTXCI6W119fX0sXCJwYWdlSW5kZXhcIjoyMCxcInR5cGVcIjpcIlBBR0lOQVRJT05cIixcInBvbGxpbmdTZXF1ZW5jZU51bVwiOjB9In0.MzJlMjUwMzMtNTIyNi00NmRkLThmNTQtNGMxYjNlMzMwNjhmLk1FWUNJUUN1VzBSeldvTVI0Q0JTQ19pam5zR1FOQXVZdUVVeEJ5U2VGTlJ1VUhGaEJnSWhBTjVpWEtBSGZaT2xxWjY0cGVYTVFLLUM1RmtIejZXWjZLc1p6X3g0S3VDZw"},"commerce":{},"sessionId":"D8C21EA5110A51D4D22C6910826C1951","tracking":{"screenName":"Attraction_Review","pageviewUid":"586564fd-30c1-44fc-b52a-f5b6660a47b0"},"currency":"RUB","currentGeoPoint":None,"unitLength":"KILOMETERS"},"extensions":{"preRegisteredQueryId":"45c77754ff77a0e7"}}
    parameters = {"variables":{"page":"Attraction_Review","pos":"ru-RU","parameters":[{"key":"geoId","value":"298484"},{"key":"detailId","value":"8514577"},{"key":"offset","value":offset}],"factors":["TITLE","META_DESCRIPTION","MASTHEAD_H1","MAIN_H1","IS_INDEXABLE","RELCANONICAL"],"route":{"page":"Attraction_Review","params":{"geoId":298484,"detailId":8514577,"offset":offset}},"currencyCode":"RUB"},"extensions":{"preRegisteredQueryId":"18d4572907af4ea5"}},{"variables":{"pageName":"Attraction_Review","relativeUrl":f"/Attraction_Review-g298484-d8514577-Reviews-o{offset}-Moskvarium-Moscow_Central_Russia.html","parameters":[{"key":"geoId","value":"298484"},{"key":"detailId","value":"8514577"},{"key":"offset","value":offset}],"route":{"page":"Attraction_Review","params":{"geoId":298484,"detailId":8514577,"offset":offset}},"routingLinkBuilding":True},"extensions":{"preRegisteredQueryId":"211573a2b002568c"}},{"variables":{"request":{"tracking":{"screenName":"Attraction_Review","pageviewUid":"fe807ec8-556b-4670-8fe4-5efecd6601ce"},"routeParameters":{"contentType":"attraction","contentId":"8514577"},"clientState":{"userInput":[{"inputKey":"rating","inputValues":["1","2","3"]},{"inputKey":"months","inputValues":[]},{"inputKey":"type","inputValues":[]}]},"updateToken":"eyJ2ZXIiOiJ2MiIsInR5cCI6IkpXVCIsImFsZyI6IkVTMjU2IiwidmVyc2lvbiI6IjEifQ.eyJvYmplY3QiOiJ7XCJAY1wiOlwiLlBhZ2luZ1VwZGF0ZVRva2VuXCIsXCJjbHVzdGVySWRzXCI6W1wiUE9JX1JFVklFV1NfV0VCXCJdLFwicHJvdmlkZXJVcGRhdGVUb2tlbnNcIjp7XCJUUkFOU0xBVEVfUkVWSUVXU1wiOntcIkBjXCI6XCJjb20udHJpcGFkdmlzb3Iuc2VydmljZS5hcHMuYWRhcHRlcnMuaG90ZWxzLlRyYW5zbGF0ZVJldmlld3NUb2tlblwiLFwic2hvdWxkVHJhbnNsYXRlXCI6dHJ1ZSxcInJldmlld0lkc1wiOlsxMDI4MjUxMTM0LDEwMjIyNjE5NDEsMTAxMTQxNTkwNCwxMDA2ODgwODIxLDEwMDU5OTM1MjIsMTAwNTc0NjIwNSw5OTQxNzIzODksOTkxNzM4ODg5LDk4ODYxMTkwMSw5ODgzNzQ2MDNdLFwidG90YWxDb3VudFwiOjU0NSxcInNob3dUcmFuc2xhdGVIZWFkZXJcIjpmYWxzZSxcImZhdm9yaXRlUmV2aWV3SWRcIjpudWxsfSxcIldFQl9SRVZJRVdTX0ZJTFRFUlwiOntcIkBjXCI6XCJjb20udHJpcGFkdmlzb3Iuc2VydmljZS5hcHMud2Vic2FuZGJveC5tb2RlbC5yZXZpZXdzYW5kcWEuV2ViUmV2aWV3c0ZpbHRlclRva2VuXCIsXCJzZWxlY3RlZEZpbHRlcnNcIjp7XCJSQVRJTkdcIjpbXCIxXCIsXCIyXCIsXCIzXCJdLFwiVFlQRVwiOltdLFwiTU9OVEhTXCI6W119fX0sXCJwYWdlSW5kZXhcIjoyMCxcInR5cGVcIjpcIlBBR0lOQVRJT05cIixcInBvbGxpbmdTZXF1ZW5jZU51bVwiOjB9In0.MzJlMjUwMzMtNTIyNi00NmRkLThmNTQtNGMxYjNlMzMwNjhmLk1FWUNJUUN1VzBSeldvTVI0Q0JTQ19pam5zR1FOQXVZdUVVeEJ5U2VGTlJ1VUhGaEJnSWhBTjVpWEtBSGZaT2xxWjY0cGVYTVFLLUM1RmtIejZXWjZLc1p6X3g0S3VDZw"},"commerce":{},"sessionId":"D8C21EA5110A51D4D22C6910826C1951","tracking":{"screenName":"Attraction_Review","pageviewUid":"fe807ec8-556b-4670-8fe4-5efecd6601ce"},"currency":"RUB","currentGeoPoint":None,"unitLength":"KILOMETERS"},"extensions":{"preRegisteredQueryId":"45c77754ff77a0e7"}},{"variables":{"page":"Attraction_Review","params":[{"key":"geoId","value":"298484"},{"key":"detailId","value":"8514577"},{"key":"offset","value":offset}],"route":{"page":"Attraction_Review","params":{"geoId":298484,"detailId":8514577,"offset":offset}}},"extensions":{"preRegisteredQueryId":"f742095592a84542"}}
    
    #print(parameters == r20)

    #input()

    # for i in parameters:
    #     #print(i)
    #
    #     if i.get('variables'):
    #         print(i['variables']['parameters'][2] == {"key":"offset","value":offset})
    #
    # input()

    response = requests.post(url, headers=headers, json=parameters)
    soup = BeautifulSoup(response.text, 'html.parser')
    python_dict = str(soup)
    json_data = json.loads(python_dict)
    #print('**********************************111**************************************')

    # pprint(json_data)
    #
    for json_d in json_data:
        if json_d['data'].get('Result'):
            blocks = json_d['data']['Result'][0]['detailSectionGroups'][0]['detailSections'][0]['tabs'][0]['content']
            #print('**********************************222**************************************')
            break
            # #pprint(blocks)

    datas = []

    for k, block in enumerate(blocks):
        #print(f'*************************{k}*******************************')
        if block.get('htmlText'):
            htmlTitle = block['htmlTitle']['text']
            htmlText = await clean_html(block['htmlText']['text'])
            feedback = f'{htmlTitle}\n{htmlText}'

            date_string = block['rawPublishedDate']
            date_obj = datetime.strptime(date_string, "%Y-%m-%d")
            date_formating = date_obj.strftime("%d.%m.%Y")

            author = block['userProfile']['localizedDisplayName']['text']

            url_answer = 'https://www.tripadvisor.ru' + block['cardLink']['webRoute']['webLinkUrl']

            rating = block['bubbleRatingNumber']

            datas.append({
                "formatted_date": date_formating,
                "author": author,
                "feedback": feedback,
                "url_answer": url_answer,
                'rating': rating
            })

    return datas


async def main():
    url = 'https://www.tripadvisor.ru/Attraction_Review-g298484-d8514577-Reviews-or40-Moskvarium-Moscow_Central_Russia.html'
    driver = await get_selenium_proxy(headless=False, proxy=False)
    datas = await blocks_tripadvisor_sel(driver, url)
    #datas = await blocks_tripadvisor(' ', 7)
    print(datas)


if "__main__" in __name__:
    asyncio.run(main())


