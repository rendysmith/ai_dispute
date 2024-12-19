
"""
https://yandex.kz/maps/org/sidorin_lab/193038195644/reviews/?ll=37.660118%2C55.740941&z=14
https://zoon.ru/msk/business/internet-agentstvo_sidorin_lab_na_taganskoj_ulitse/reviews/
https://dreamjob.ru/employers/58176
"""
import asyncio
import os
import time

import textwrap

from requests.auth import HTTPBasicAuth

from portals.dreamjob import get_full_feedback
from portals.portal_ya import get_json

from models.mdl_tables import ForumRules, Prompt
from utils.ai_module import get_answer_ai
from utils.central_module import get_local_ip
from utils.db_loader import read_data_from_db_filter
from utils.gs_editor import get_service, append_data_to_sheet_scope, pars_url
from utils.user_agent import get_soup, get_selenium_proxy

auth_username = os.environ.get("HOST_USERNAME")
auth_password = os.environ.get("HOST_PASSWORD")
auth = HTTPBasicAuth(auth_username, auth_password)

worktable_id = '1wLn7fQ2omM6_mzY7v1iAqQWzQqMpbo2odDLg7LrnMm8'
worksheet_name = 'Sidorin'

local_ip = asyncio.run(get_local_ip())
if '176.124.192' in local_ip:
    headless = True
    proxy_on = True
    only_text = False

else:
    print(f'local_ip: {local_ip}')
    headless = True
    proxy_on = False
    only_text = False

async def get_rules():
    pass

async def record_data(service, url_answer, prompt_text, project, comment, rule):
    prompt = prompt_text.format(source=project, comment=comment, rule=rule)
    result = await get_answer_ai(auth, prompt)

    try:
        result = eval(result)
        print(result)

        datas = {'Portal': project,
                 'Link': url_answer,
                 'Perc': result[0],
                 'Feedback': comment,
                 'Text': result[1]}

        await append_data_to_sheet_scope(service,
                                         worktable_id,
                                         worksheet_name,
                                         datas)

    except Exception as Ex:
        print(f'Error Ex: {Ex}')

async def analyst_zoon(service, links, prompt_text):
    project = 'zoon'

    status, rules_db = await read_data_from_db_filter(ForumRules, forum_name=project)
    if status:
        if len(rules_db) > 0:
            rule = rules_db[0].forum_rule

        else:
            print(f'{project} No rules')
            return

    else:
        return

    company_url = 'https://zoon.ru/msk/business/internet-agentstvo_sidorin_lab_na_taganskoj_ulitse/reviews/?sort=rating_asc'

    soup = await get_soup(company_url, proxy=proxy_on)

    blocks = soup.find_all('li', {'class': 'comment-item js-comment'})
    len_b = len(blocks)

    if len_b == 0:
        return

    print(len_b)

    for block in blocks:
        try:
            raiting = block.find('div', {'data-uitest': 'personal-mark'}).text.replace(',', '.')
            raiting = float(raiting)

        except:
            continue

        data_id = block.get('data-id')

        if data_id in links:
            continue

        if raiting <= 3.5:
            comment_content = block.find('div', {'class': 'comment-item__body js-comment-text'})
            #print(comment.text)

            comment = textwrap.fill(comment_content.text)
            await record_data(service, data_id, prompt_text, project, comment, rule)

async def analyst_yandex(service, links, prompt_text):
    project = 'yandex_maps'

    status, rules_db = await read_data_from_db_filter(ForumRules, forum_name=project)
    if status:
        if len(rules_db) > 0:
            rule = rules_db[0].forum_rule

        else:
            print(f'{project} No rules')
            return

    else:
        return

    company_url = 'https://yandex.kz/maps/org/sidorin_lab/193038195644/reviews'

    driver = await get_selenium_proxy(headless=headless, proxy=proxy_on)
    ss_id = None
    rating_ranking = 2
    dictionary = await get_json(service, company_url, ss_id, project, driver, rating_ranking)

    if not isinstance(dictionary, dict):
        return

    try:
        driver.quit()
    except:
        pass

    if dictionary.get('data'):
        if dictionary['data'].get('reviews'):
            reviews = dictionary['data']['reviews']
        else:
            return

    else:
        return

    len_r = len(reviews)
    print(f'Len_r: {len_r}')
    if len_r == 0:
        return None

    for rew in reviews:
        reviewId = rew['reviewId']
        if reviewId in links:
            print('- Такой комментарий уже есть.')
            continue

        raiting = rew['rating']
        if raiting <= 3.5:
            print(f'Rating = {raiting}')
            comment = rew['text']
            await record_data(service, reviewId, prompt_text, project, comment, rule)

async def analyst_dreamjob(service, links, prompt_text):
    project = 'dreamjob'

    status, rules_db = await read_data_from_db_filter(ForumRules, forum_name=project)
    if status:
        if len(rules_db) > 0:
            rule = rules_db[0].forum_rule

        else:
            print(f'{project} No rules')
            return

    else:
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
            raiting = block.find('div', {'class': 'dj-rating dj-rating--35'})

            if raiting:
                url_answer = block.find('a', {'class': 'bt bt--32 bt--primary-link icon-copy'}).get('href')
                if not url_answer:
                    url_answer = block.find('a', role='button', tabindex='0').get('href')

                if not url_answer:
                    url_answer = block.find('a', tabindex='0').get('href')

                if url_answer in links:
                    print('-- Ссылка уже есть в таблице')
                    continue

                #print(raiting)
                rait = float(raiting.text.strip().replace(',', '.'))
                print(rait)
                if rait <= 3.5: #Тут должна быть 3,5
                    comment = await get_full_feedback(block)
                    await record_data(service, url_answer, prompt_text, project, comment, rule)

async def main_sidorin():
    service = await get_service()

    #Уже опрошенные ссылки
    links = await pars_url(service, worktable_id, worksheet_name)

    #Промпт для анализа
    status, text_prompt = await read_data_from_db_filter(Prompt, project_name='sidorin')
    if status:
        prompt_text = text_prompt[0].prompt

        print('- Analyst Dreamjob')
        await analyst_dreamjob(service, links, prompt_text)

        print('- Analyst Zoon')
        await analyst_zoon(service, links, prompt_text)

        print('- Analyst Ya Maps')
        await analyst_yandex(service, links, prompt_text)

    else:
        return

if "__main__" == __name__:
    asyncio.run(main_sidorin())
