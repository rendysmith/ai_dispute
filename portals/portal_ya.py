from urllib.parse import urlparse, urlunparse


async def get_rrr(json_data):
    async def get_3r(i):
        # print("LenI", len(i['items']))
        ratingValue = round(i['items'][0]['ratingData']['ratingValue'], 1)
        review_count = i['items'][0]['ratingData']['reviewCount']
        rating_count = i['items'][0]['ratingData']['ratingCount']
        # print(ratingValue, review_count, rating_count)
        return ratingValue, review_count, rating_count

    if json_data.get('stack'):
        for i1 in json_data['stack']:
            if i1.get('results'):
                res = i1['results']
                return await get_3r(res)

            elif i1.get('response'):
                res = i1['response']
                return await get_3r(res)


async def get_base_url(url):
    """
    GET base url
    example https://yandex.kz/maps/org/dpd/46397060555
    :param url:
    :return:
    """
    parsed = urlparse(url)
    # Возвращаем только схему, домен и путь (без query и fragment)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
