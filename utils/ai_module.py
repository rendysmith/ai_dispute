import asyncio
import random
import json
import time
import os
import traceback

import google.generativeai as genai
import google.api_core.exceptions
import requests
from dotenv import load_dotenv

from requests.auth import HTTPBasicAuth

import httpx

from utils.db_loader import get_api_tokens, get_hosts
from utils.gs_editor import append_data_to_sheet_scope
from utils.constants import farm_hosts

async def get_answer_gemini_old(prompt: str, engine: str):
    """
    gemini-pro - Ограничение
    15 RPM - Requests per minute
    32,000 TPM - Tokens per minute
    1,500 RPD - Requests per day
    46,080,000 TPD - Tokens per day

    gemini-1.5-flash - Ограничение
    15 RPM
    1 million TPM
    1500 RPD

    gemini-1.5-pro - Ограничение
    2 RPM
    32,000 TPM
    50 RPD
    46,080,000 TPD
    """
    genai.configure(api_key=GEMINI_TOKEN)
    model = genai.GenerativeModel(engine)

    try:
        response = model.generate_content(prompt)
        #print(f"Type of response: {type(response)}") # Проверяем тип ответа
        #print(response.__dict__) # Выводим структуру ответа

        # Получаем текст из кандидатов
        candidates = response.candidates
        full_text = ""
        for candidate in candidates:
            if candidate.content:
                text_parts = candidate.content.parts
                full_text += "".join([part.text for part in text_parts])
        return full_text

    except google.api_core.exceptions.InternalServerError as ISE:
        print(f'ERROR ISE: {ISE}')
        return str(ISE)
        #time.sleep(10)
        #attempt += 1

    except ValueError as VE:
        print("ERROR VE", VE)
        return str(VE)

async def get_answer_gemini_local(prompt: str, engine: str, token = 'AIzaSyAFHcCXEOSIWdXdlxNelqzjoiT1CNJB8kQ'):
    engine = engine.lower()
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{engine}:generateContent?key={token}'
    headers = {'Content-Type': 'application/json'}
    data = {
        'contents': [
            {
                'parts': [
                    {
                        'text': prompt
                    }
                ]
            }
        ]
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    r_json = response.json()
    #print("r_json:", r_json)
    status_code = response.status_code
    if status_code == 200:
        if not r_json['candidates'][0].get('content'):
            return status_code, r_json

        result = r_json['candidates'][0]['content']['parts'][0]['text']
        return status_code, result

    else:
        result = r_json['error']['message']
        return status_code, result


async def get_answer_ai(auth: HTTPBasicAuth, prompt: str):
    #farm_hosts = await get_hosts()
    #gemini_tokens = await get_api_tokens()

    try_n = 0
    while True:
        try:
            random_host = random.choice(farm_hosts)
            # random_token = random.choice(gemini_tokens)
            # print(random_host, random_token)

            url = f"http://{random_host}:8000/api/v1/start_generation"
            data = {
                "prompt": prompt
            }

            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, json=data, auth=auth)

            if response.status_code == 200:
                result = response.json()['result']
                print('OK!')
                return result

            else:
                print(response.status_code, response.text)
                if try_n == 10:
                    return f"{random_host} {response.status_code}"

                try_n += 1
                await asyncio.sleep(1)

        except requests.exceptions.ConnectionError as CE:
            print('ERROR HOST:', random_host)

            if try_n == 10:
                return f"{random_host} {response.status_code}"

            try_n += 1
            await asyncio.sleep(1)

        except httpx.ReadTimeout as RT:
            print(f'ERROR AI RT: {RT}')
            traceback.print_exc()
            if try_n == 10:
                return f"{random_host} {response.status_code} {RT}"

            try_n += 1
            await asyncio.sleep(1)

        except Exception as Ex:
            print(f'ERROR AI Ex: {Ex}\n{farm_hosts}')
            traceback.print_exc()

            if try_n == 10:
                return f"{random_host} {response.status_code}"

            try_n += 1
            await asyncio.sleep(1)

    #return None

# auth = HTTPBasicAuth('anku@sidorinlab.ru', 'pass')
# a = asyncio.run(get_answer_gemini(auth, "Какой вес у Солнца?", "gemini-1.5-flash"))
# print(a)

async def get_answer_gemini_old2(auth: HTTPBasicAuth, prompt: str, engine: str):
    """
    gemini-pro - Ограничение
    15 RPM - Requests per minute
    32,000 TPM - Tokens per minute
    1,500 RPD - Requests per day
    46,080,000 TPD - Tokens per day

    gemini-1.5-flash - Ограничение
    15 RPM
    1 million TPM
    1500 RPD

    gemini-1.5-pro - Ограничение
    2 RPM
    32,000 TPM
    50 RPD
    46,080,000 TPD
    """

    farm_hosts = await get_hosts()
    gemini_tokens = await get_api_tokens()

    try_n = 0
    while True:
        try:
            random_host = random.choice(farm_hosts)
            random_token = random.choice(gemini_tokens)
            print(random_host, random_token)

            url = f"http://{random_host}:8000/api/v1/start_generation"
            data = {
                "prompt": prompt,
                "token": random_token,
                "engine": engine
            }

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=data, auth=auth)

            if response.status_code == 200:
                result = response.json()['result']
                print('OK!')
                return result

            else:
                if try_n == 10:
                    return f"{random_host} {response.status_code}"

                try_n += 1
                await asyncio.sleep(1)

        except requests.exceptions.ConnectionError as CE:
            print('ERROR HOST:', random_host)

            if try_n == 10:
                return f"{random_host} {response.status_code}"

            try_n += 1
            await asyncio.sleep(1)

        except Exception as Ex:
            print(f'ERROR Ex: {Ex}')

            if try_n == 10:
                return f"{random_host} {response.status_code}"

            try_n += 1
            await asyncio.sleep(1)

async def get_answer_gpt(prompt: str):
    model = 'gpt-4o-mini'
    endpoint = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GPT_TOKEN}"
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    response = requests.post(endpoint, headers=headers, json=data)
    status_code = response.status_code

    r_json = response.json()

    if status_code == 200:
        try:
            return r_json['choices'][0]['message']['content']

        except requests.exceptions.JSONDecodeError as JDE:
            print(f'ERROR: {JDE}')
            return None

    elif status_code == 400:
        error_400 = f"Error 400\n{r_json['error']['message']}"
        return error_400

    elif status_code == 429:
        error_429 = f"Error 429\n{r_json['error']['message']}\nhttps://platform.openai.com/usage"
        return error_429

    else:
        print(f"Error: {status_code}\n{r_json}")
        return None

def generate_and_white_sync(**kwargs):
    service = kwargs["service"]
    url_answer = kwargs["url_answer"]
    author = kwargs["author"]
    formatted_date = kwargs["formatted_date"]
    ss_id = kwargs["ss_id"]
    project = kwargs["project"]
    feedback = kwargs["feedback"]
    pattern = kwargs["pattern"]
    criteria = kwargs["criteria"]

    start_time = time.time()

    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    load_dotenv(dotenv_path)

    username = os.environ.get("HOST_USERNAME")
    password = os.environ.get("HOST_PASSWORD")
    auth = HTTPBasicAuth(username, password)

    prompt = f"""
    Ты официальный представить компании '{project}'
    Твоя задача: 
    1 - прочитать комментарий о компании:
    -----------Начало комментария--------------
    {feedback}
    ----------Конец комментария----------------   
    2 - Напишите ответ на комментарий, который будет личным, сопереживающим и демонстрирующим разговорный тон. 
    В идеале ответ должен звучать так, будто он исходит от реального человека, 
    а не от механического сценария. 
    Пожалуйста, составьте ответ, который признает точку зрения комментатора, 
    демонстрирует понимание и приглашает к дальнейшему обсуждению. 
    Стремитесь к тому, чтобы ответ был теплым, доступным и увлекательным, но при этом передавал необходимую информацию и контекст
    Дополнительно для примера можешь использовать шаблоны:
    ----------Начало шаблонов -----------------
    {pattern}
    ----------Конец шаблонов ------------------
    Так же необходимо учитывать следующее:
    {criteria}
    Дополнительно:
    - Не пиши слишком развернуто 
    - Не цитируй слова из комментария.
    """

    result = asyncio.run(get_answer_ai(auth, prompt))
    if result == False:
        return

    print(f'TIMER {round(time.time() - start_time, 2)}')

    data = {
        'Link': url_answer,
        'Author': author,
        'Date': formatted_date,
        'Feedback': feedback,
        'Results': result
    }

    #print(data)

    status = asyncio.run(append_data_to_sheet_scope(service, ss_id, project, data))
    print(status)

async def generate_and_white(**kwargs):
    service = kwargs["service"]
    url_answer = kwargs["url_answer"]
    author = kwargs["author"]
    formatted_date = kwargs["formatted_date"]
    ss_id = kwargs["ss_id"]
    project = kwargs["project"]
    feedback = kwargs["feedback"]
    pattern = kwargs["pattern"]
    criteria = kwargs["criteria"]

    start_time = time.time()

    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    load_dotenv(dotenv_path)

    username = os.environ.get("HOST_USERNAME")
    password = os.environ.get("HOST_PASSWORD")
    auth = HTTPBasicAuth(username, password)

    prompt = f"""
    Ты официальный представить компании '{project}'
    Твоя задача: 
    1 - прочитать комментарий о компании:
    -----------Начало комментария--------------
    {feedback}
    ----------Конец комментария----------------   
    2 - Напишите ответ на комментарий, который будет личным, сопереживающим и демонстрирующим разговорный тон. 
    В идеале ответ должен звучать так, будто он исходит от реального человека, 
    а не от механического сценария. 
    Пожалуйста, составьте ответ, который признает точку зрения комментатора, 
    демонстрирует понимание и приглашает к дальнейшему обсуждению. 
    Стремитесь к тому, чтобы ответ был теплым, доступным и увлекательным, но при этом передавал необходимую информацию и контекст
    Дополнительно для примера можешь использовать шаблоны:
    ----------Начало шаблонов -----------------
    {pattern}
    ----------Конец шаблонов ------------------
    Так же необходимо учитывать следующее:
    {criteria}
    Дополнительно:
    - Не пиши слишком развернуто 
    - Не цитируй слова из комментария.
    """

    result = await get_answer_ai(auth, prompt)
    if result == False:
        return

    print(f'TIMER {round(time.time() - start_time, 2)}')

    data = {
        'Link': url_answer,
        'Author': author,
        'Date': formatted_date,
        'Feedback': feedback,
        'Results': result
    }

    #print(data)

    status = await append_data_to_sheet_scope(service, ss_id, project, data)
    print(status)

# Пример использования функции
# user_message = "Какое расстояние от земли до солнца?"
# completion = get_txt(user_message)
# print(completion)
#
# r = asyncio.run(get_answer_gpt('Кто такой Илон Маск?'))
# print(r)
#
# def get_models():
#     openai.api_key = GPT_TOKEN
#     models = openai.models.list()
#     model_json = eval(models.json())
#     print(model_json)
#
#     df = pd.DataFrame(model_json['data'])
#     df = df.sort_values(by='id').reset_index(drop=True)
#     print(df)
#
# def get_txt_old(prompt: str, model:str):
#     openai.api_key = os.environ[GPT_TOKEN]
#     #openai.api_key = GPT_TOKEN
#     model = 'text-davinci-003'
#     max_tokens = 2048
#
#     completion = openai.Completion.create(
#         engine=model,
#         prompt=prompt,
#         max_tokens=max_tokens,
#         temperature=0
#     )
#     txt = completion.choices[0].text
#     return txt
#
# def get_txt2(prompt: str, max_tokens: int):
#     # Передайте ключ API при создании объекта клиента
#     client = Client(api_key=GPT_TOKEN)
#
#     stream = client.chat.completions.create(
#         model="gpt-4",
#         messages=[{"role": "user", "content": prompt}],
#         stream=True,
#         max_tokens=max_tokens
#     )
#
#     generated_text = ""
#     for chunk in stream:
#         if chunk.choices[0].delta.content is not None:
#             print(chunk.choices[0].delta.content, end="")
#             generated_text += chunk.choices[0].delta.content
#
#     return generated_text
#
# def get_balance():
#
#     """curl -X GET https://api.openai.com/dashboard/billing/credit_grants \
#      -H "Content-Type: application/json" \
#      -H "Authorization: Bearer sess-xxxx"""
#
#     url = 'https://api.openai.com/dashboard/billing/credit_grants'
#
#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"Bearer {GPT_TOKEN}"
#     }
#
#     response = requests.get(url, headers=headers)
#
#     print(response.json())

#
# def gpt_moderator(prompt: str):
#     openai.api_key = GPT_TOKEN
#     response = openai.moderations.create(prompt)
#     result = response
#     #print(result)
#
# def get_models_gemini():
#     genai.configure(api_key=GEMINI_TOKEN)
#     for m in genai.list_models():
#         if 'generateContent' in m.supported_generation_methods:
#             print(m.name)
#
# def get_quota():
#     genai.configure(api_key=GEMINI_TOKEN)
#     usage = genai.get
#
#     # Преобразуем ответ в JSON
#     data = json.loads(usage)
#
#     # Извлекаем количество оставшихся запросов
#     remaining_requests = data["remaining_requests"]
#
#     # Печатаем количество оставшихся запросов
#     print(f"Оставшееся количество запросов: {remaining_requests}")
#     print(f"Осталось запросов: {remaining_requests}")
#
# def get_answer_replicate(prompt: str, engine: str):
#     input = {
#         "top_p": 1,
#         "prompt": "Can you write a poem about open source machine learning? Let's make it in the style of E. E. Cummings.",
#         "temperature": 0.5,
#         "system_prompt": "You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe. Your answers should not include any harmful, unethical, racist, sexist, toxic, dangerous, or illegal content. Please ensure that your responses are socially unbiased and positive in nature.\n\nIf a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information.",
#         "max_new_tokens": 500
#     }
#
#     for event in replicate.stream(
#             "meta/llama-2-70b-chat",
#             input=input
#     ):
#         print(event, end="")
#
#
# async def get_answer_gemini_old(prompt: str, engine: str):
#     """
#     gemini-pro - Ограничение
#     15 RPM - Requests per minute
#     32,000 TPM - Tokens per minute
#     1,500 RPD - Requests per day
#     46,080,000 TPD - Tokens per day
#
#     gemini-1.5-flash - Ограничение
#     15 RPM
#     1 million TPM
#     1500 RPD
#
#     gemini-1.5-pro - Ограничение
#     2 RPM
#     32,000 TPM
#     50 RPD
#     46,080,000 TPD
#     """
#     genai.configure(api_key=GEMINI_TOKEN)
#     model = genai.GenerativeModel(engine)
#     attempt = 0
#     while attempt < 10:
#         try:
#             response = model.generate_content(prompt)
#             break
#
#         except google.api_core.exceptions.InternalServerError as ISE:
#             print(f'ERROR: {ISE}')
#             time.sleep(10)
#             attempt += 1
#
#     try:
#         return response.text
#
#     except ValueError as VE:
#         print(VE)
#         return str(VE)
