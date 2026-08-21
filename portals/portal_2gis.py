async def get_id_obj(url):
    url_split = url.split('/')
    # city_company = url_split[3]

    id_obj = ''
    for idx, v in enumerate(url_split):
        if v == 'firm':
            id_obj = url_split[idx + 1]
            break

        elif v == 'orgs':
            id_obj = url_split[idx + 1]
            break

        elif v == 'geo':
            id_obj = url_split[idx + 1]
            break

        elif v == "reviews":
            id_obj = url_split[idx + 1]
            break

    return id_obj.strip()
