
"""
https://yandex.kz/maps/org/sidorin_lab/193038195644/reviews/?ll=37.660118%2C55.740941&z=14
https://zoon.ru/msk/business/internet-agentstvo_sidorin_lab_na_taganskoj_ulitse/reviews/
https://dreamjob.ru/employers/58176
"""
import asyncio
import os
import time

from requests.auth import HTTPBasicAuth

from models.mdl_tables import ForumRules, Prompt
from portals.dreamjob import get_full_feedback
from utils.ai_module import get_answer_ai
from utils.db_loader import read_data_from_db_filter
from utils.gs_editor import get_service, append_data_to_sheet_scope
from utils.user_agent import get_soup

auth_username = os.environ.get("HOST_USERNAME")
auth_password = os.environ.get("HOST_PASSWORD")
auth = HTTPBasicAuth(auth_username, auth_password)

worktable_id = '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8'
worksheet_name = 'Sidorin'

proxy_on = False
only_text = False

async def analyst_dreamjob(service, prompt_text):
    project = 'dreamjob'

    status, rules_db = await read_data_from_db_filter(ForumRules, forum_name=project)
    if status:
        if len(rules_db) > 0:
            rule = rules_db[0].forum_rule

        else:
            print(f'{project} No rules')
            return

    company_url = 'https://dreamjob.ru/employers/58176'

    unix_time = str(int(time.time() * 1000))

    pages = ['1']

    for page in pages:
        url = f'{company_url}?employerId=58176&erfrp%5BlastParam%5D=&erfrp%5Bfrom_vacancy%5D=&sort=total_rating&page={page}&_={unix_time}'

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
                url_answer = block.find('a', {'class': 'bt bt--32 bt--primary-link icon-copy'}).get('href')
                if not url_answer:
                    url_answer = block.find('a', role='button', tabindex='0').get('href')

                if not url_answer:
                    url_answer = block.find('a', tabindex='0').get('href')

                #print(raiting)
                rait = float(raiting.text.strip().replace(',', '.'))
                print(rait)
                if rait <= 3.8: #Тут должна быть 3,5
                    comment = await get_full_feedback(block)

                    prompt = prompt_text.format(source=project, comment=comment, rule=rule)
                    result = await get_answer_ai(auth, prompt)

                    try:
                        result = eval(result)
                        print(result)

                        datas = {'url': url_answer,
                                 'perc': result[0],
                                 'text': result[1]}

                        await append_data_to_sheet_scope(service,
                                                          worktable_id,
                                                          worksheet_name,
                                                          datas)


                    except:
                        pass





async def check_sidorin():
    service = await get_service()
    status, text_prompt = await read_data_from_db_filter(Prompt, project_name='sidorin')
    if status:
        prompt_text = text_prompt[0].prompt
        await analyst_dreamjob(service, prompt_text)

    else:
        return



if "__main__" == __name__:
    asyncio.run(check_sidorin())
