
"""
https://yandex.kz/maps/org/sidorin_lab/193038195644/reviews/?ll=37.660118%2C55.740941&z=14
https://zoon.ru/msk/business/internet-agentstvo_sidorin_lab_na_taganskoj_ulitse/reviews/
https://dreamjob.ru/employers/58176
"""
import asyncio
import time

from ai.  import

from utils.user_agent import get_soup

proxy_on = False
only_text = False


async def analyst_dreamjob():
    company_url = 'https://dreamjob.ru/employers/58176'

    unix_time = str(int(time.time() * 1000))

    pages = ['1']

    for page in pages:
        url = f'{company_url}?employerId=58176&erfrp%5BlastParam%5D=&erfrp%5Bfrom_vacancy%5D=&sort=-total_rating&page={page}&_={unix_time}'

        soup = await get_soup(url, proxy=proxy_on)
        if not soup:
            continue

        blocks = soup.find_all('div', {"class": 'review', 'data-partly': 'short'})
        print('Len:', len(blocks))
        if len(blocks) == 0:
            return None

        for block in blocks:
            print('\n*******************************************')
            raiting = block.find('div', {'class': 'dj-rating dj-rating--35'})

            if raiting:
                print(raiting)
                print(raiting.text)


                feedback = await





async def check_sidorin():
    await analyst_dreamjob()



if "__main__" == __name__:
    asyncio.run(check_sidorin())
