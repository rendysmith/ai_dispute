import asyncio
import os
import traceback

import httpx
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

from models.mdl_tables import Tokens
from utils.db_loader import read_data_from_db_filter_limit

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

# Токен и модель GPT грузятся из БД лениво (при первом вызове get_answer_ai),
# т.к. под uvicorn модуль импортируется внутри запущенного event loop.
_gpt_api_token = None
_gpt_model = None
_token_lock = asyncio.Lock()


async def _ensure_token():
    global _gpt_api_token, _gpt_model
    if _gpt_api_token:
        return

    async with _token_lock:
        if _gpt_api_token:
            return

        status, rows = await read_data_from_db_filter_limit(
            Tokens,
            limit=1,
            page=1,
            username='chat_gpt',
        )
        if not status or not rows:
            raise RuntimeError(f'Не удалось загрузить токен GPT из БД: {rows}')

        _gpt_api_token = rows[0].api_token
        _gpt_model = rows[0].model


async def get_answer_ai(auth: HTTPBasicAuth, prompt: str, username: str = 'chat_gpt'):
    await _ensure_token()

    endpoint = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_gpt_api_token}",
    }
    data = {
        "model": _gpt_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    }

    try_n = 0
    while try_n <= 10:
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(endpoint, headers=headers, json=data)

            if response.status_code == 200:
                result = response.json()["choices"][0]["message"]["content"]
                print("OK!")
                return result

            try:
                error_message = response.json().get("error", {}).get("message", response.text)
            except Exception:
                error_message = response.text

            if response.status_code in (429, 500, 502, 503) and try_n < 10:
                try_n += 1
                await asyncio.sleep(1)
                continue

            return f"OpenAI {response.status_code}: {error_message}"

        except httpx.ReadTimeout as RT:
            print(f"ERROR AI RT: {RT}")
            if try_n == 10:
                return f"OpenAI timeout: {RT}"
            try_n += 1
            await asyncio.sleep(1)

        except Exception as Ex:
            print(f"ERROR AI Ex: {Ex}")
            traceback.print_exc()
            if try_n == 10:
                return f"OpenAI error: {Ex}"
            try_n += 1
            await asyncio.sleep(1)

    return False
