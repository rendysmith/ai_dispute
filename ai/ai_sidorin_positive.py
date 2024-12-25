"""
https://yandex.kz/maps/org/sidorin_lab/193038195644/reviews/?ll=37.660118%2C55.740941&z=14
https://zoon.ru/msk/business/internet-agentstvo_sidorin_lab_na_taganskoj_ulitse/reviews/
https://dreamjob.ru/employers/58176
"""
import ast
import asyncio
import os
import time

import textwrap

import pandas as pd
from requests.auth import HTTPBasicAuth

from selenium.webdriver.common.by import By

from portals.dreamjob import get_full_feedback, get_raiting
from portals.portal_ya import get_json, click_checkbox

from models.mdl_tables import ForumRules, Prompt
from utils.ai_module import get_answer_ai
from utils.central_module import get_local_ip
from utils.db_loader import read_data_from_db_filter
from utils.gs_editor import get_service, append_data_to_sheet_scope, pars_url, get_table_scope, \
    append_data_to_sheet_cell
from utils.user_agent import get_soup, get_selenium_proxy

from utils.constants import TABLES_LIST

auth_username = os.environ.get("HOST_USERNAME")
auth_password = os.environ.get("HOST_PASSWORD")
auth = HTTPBasicAuth(auth_username, auth_password)

worksheet_name = 'Sidorin'
worktable_id = TABLES_LIST[worksheet_name]

local_ip = asyncio.run(get_local_ip())
if '176.124.192' in local_ip:
    headless = True
    proxy_on = True
    only_text = False

else:
    print(f'local_ip: {local_ip}')
    headless = False
    proxy_on = False
    only_text = False

async def total_grade_analysis(service):
    '''Функция для подсчета рейтинга после удаления отзыва'''
    df = await get_table_scope(service, worktable_id, worksheet_name)

    data_rows = []

    for idx, row in df.iterrows():
        company_link = row['Portal']
        feedback_counts = row['Total']

        if pd.isna(feedback_counts):
            # print('Next...')
            continue

        #df = df[(df[add_column] == '') & (df[add_column_2].str.contains(r'([5-9][0-9]|[1-9][0-9]{2,})'))]
        df_mini = df[(df['Portal'] == company_link) & (df['Perc'].str.contains(r'([5-9][0-9]|[1-9][0-9]{2,})'))]

        df_mini = df_mini.drop_duplicates(subset=["Link"]) #Удаляем дублика ссылок!!!!!!!!!!!!!!!!!!!!!!
        df_mini["Reiting"] = pd.to_numeric(df_mini["Reiting"], errors='coerce')  # Преобразуем в числа

        counts_feedback = float(df_mini['Total'].iloc[-1])
        company_rating = float(df_mini['Pre'].iloc[-1])

        total_sum = counts_feedback * company_rating
        total_negative_sum = df_mini["Reiting"].sum()
        total_negative_count = df_mini["Reiting"].count()

        finish_sum = total_sum - total_negative_sum
        finish_counts = counts_feedback - total_negative_count
        finish_rating = round(finish_sum / finish_counts, 1)

        for idx_mini, row_mini in df_mini.iterrows():
            rating = row_mini['Post']

            if pd.notnull(rating):
                continue

            if idx_mini not in data_rows:
                await append_data_to_sheet_cell(service, worktable_id, worksheet_name,'Post', idx_mini + 2, finish_rating)
                print(f'{idx_mini} Add info...')
                data_rows.append(idx_mini)

async def record_data(service, url_answer, prompt_text, project, comment, rule, reiting, total, pre_r):
    prompt = prompt_text.format(source=project, comment=comment, rule=rule)

    results = {}
    for i in range(3):
        result = await get_answer_ai(auth, prompt)
        print(i, result)
        try:
            print('- Eval')
            result_eval = eval(result)
            print('-- Eval')

        except:
            print('- Ast')
            result_eval = ast.literal_eval(result)
            print('-- Ast')

        results[f"result_{i}"] = result_eval

    try:
        datas = {
            'Portal': project,
            'Link': url_answer,
            'Reiting': reiting,
            'Feedback': comment,
            'Perc': results['result_0'][0],
            'Text_1': results['result_0'][1],
            'Text_2': results['result_1'][1],
            'Text_3': results['result_2'][1],
            'Total': total,
            'Pre': pre_r
        }

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

    total_content = soup.find('span', {'data-target': 'marks-total'}).text
    total = int(total_content)
    print(f'Total: {total}')

    pre_content_1 = soup.find('div', {'data-target': 'rating-total'}).text
    pre_1 = float(pre_content_1.replace(',', '.'))
    print(f'Pre 1: {pre_1}')

    pre_content_2 = soup.find('div', {'class': 'z-text--16 z-text--default z-text--bold'}).text
    pre_2 = float(pre_content_2.replace(',', '.'))
    print(f'Pre 2: {pre_2}')

    if pre_1 != pre_2:
        pre_r = max(pre_1, pre_2)

    else:
        pre_r = pre_2

    blocks = soup.find_all('li', {'class': 'comment-item js-comment'})
    len_b = len(blocks)

    if len_b == 0:
        return

    print("Len_B =", len_b)

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
            comment = textwrap.fill(comment_content.text)

            print('pre_r', pre_r)
            await record_data(service, data_id, prompt_text, project, comment, rule, raiting, total, pre_r)

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

    driver = await get_selenium_proxy(company_url, headless=headless, proxy=proxy_on)
    await asyncio.sleep(5)

    await click_checkbox(driver)
    await asyncio.sleep(5)

    try:
        total_content = driver.find_element(By.CSS_SELECTOR, 'span[class=business-rating-amount-view _summary]')
    except:
        total_content = driver.find_element(By.CSS_SELECTOR, 'div[class=business-summary-rating-badge-view__rating-count]')

    total = int(total_content.text.split(' ')[0])

    pre_contents = driver.find_elements(By.CSS_SELECTOR, 'span.business-summary-rating-badge-view__rating-text')
    pre_r = float(f"{pre_contents[0].text}.{pre_contents[2].text}")

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
        if 0 < raiting <= 3.5:
            print(f'Rating = {raiting}')
            comment = rew['text']
            await record_data(service, reviewId, prompt_text, project, comment, rule, raiting, total, pre_r)

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

        if page == '1':
            total, pre = await get_raiting(soup)
            print(total, pre)

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
                raiting = float(raiting.text.strip().replace(',', '.'))
                print(raiting)
                if raiting <= 3.5: #Тут должна быть 3,5
                    comment = await get_full_feedback(block)
                    await record_data(service, url_answer, prompt_text, project, comment, rule, raiting, total, pre)

async def main_sidorin():
    service = await get_service()

    #Уже опрошенные ссылки
    links = await pars_url(service, worktable_id, worksheet_name)

    #Промпт для анализа
    status, text_prompt = await read_data_from_db_filter(Prompt, project_name='sidorin')
    if status:
        prompt_text = text_prompt[0].prompt

        print('\n- Analyst Zoon')
        await analyst_zoon(service, links, prompt_text)

        print('\n- Analyst Dreamjob')
        await analyst_dreamjob(service, links, prompt_text)

        print('\n- Analyst Ya Maps')
        await analyst_yandex(service, links, prompt_text)

        print('\n- Total grade analysis')
        await total_grade_analysis(service)

    else:
        return

if "__main__" == __name__:
    asyncio.run(main_sidorin())
