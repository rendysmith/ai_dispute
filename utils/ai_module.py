import asyncio
import time

import google.api_core.exceptions
import pandas as pd
import requests
import openai
from openai import OpenAI, Client
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
#import replicate
import os
from utils.constants import GEMINI_TOKEN, GPT_TOKEN, REPLICATE_TOKEN


async def get_answer_gemini(prompt: str, engine: str):
    """
    gemini-1.5-pro - Ограничение скорости	1 запрос в минуту, 50 запросов в день
    gemini-pro - Ограничение скорости	60 запросов в минуту
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

    except google.api_core.exceptions.ResourceExhausted as RE:
        print(f'ERROR RE: {RE}')
        return None

    except google.api_core.exceptions.InternalServerError as ISE:
        print(f'ERROR ISE: {ISE}')
        return None
        #time.sleep(10)
        #attempt += 1

    except ValueError as VE:
        print("ERROR VE", VE)
        return None

async def get_answer_gemini_(prompt: str, engine: str):
    """
    gemini-1.5-pro - Ограничение скорости	1 запрос в минуту, 50 запросов в день
    gemini-pro - Ограничение скорости	60 запросов в минуту
    """
    genai.configure(api_key=GEMINI_TOKEN)
    model = genai.GenerativeModel(engine)
    attempt = 0
    while attempt < 10:
        try:
            response = model.generate_content(prompt)
            break
        except google.api_core.exceptions.InternalServerError as ISE:
            print(f'ERROR: {ISE}')
            time.sleep(10)
            attempt += 1

    try:
        return response.text

    except ValueError as VE:
        print("ERROR VE", VE)
        return str(VE)



async def get_answer_gpt(prompt: str, model: str):
    #model = 'text-davinci-003'
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

# Пример использования функции
# user_message = "Какое расстояние от земли до солнца?"
# completion = get_txt(user_message)
# print(completion)

#asyncio.run(get_answer_gpt(prompt: str, ''))


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


#def get_answer_replicate(prompt: str, engine: str):
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

#def gpt_moderator(prompt: str):
#     openai.api_key = GPT_TOKEN
#     response = openai.moderations.create(prompt)
#     result = response
#     print(result)
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
