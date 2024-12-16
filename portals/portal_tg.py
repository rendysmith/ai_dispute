import os
import asyncio
import time
from datetime import datetime

from dotenv import load_dotenv
from pyrogram import Client

from utils.central_module import rec_data

current_path = os.path.dirname(os.path.abspath(__file__))

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

api_id = os.environ.get("TG_API_ID")
api_hash = os.environ.get("TG_API_HASH")

bot_name = os.environ.get("TG_BOT_NAME")
session_string = os.environ.get("TG_SESSION_STRING")

async def convert_time(date_str: str):
    date_format = "%d.%m %H:%M:%S"
    # Преобразование строки в datetime
    result = datetime.strptime(date_str, date_format)

    year_now = datetime.now().year
    result = result.replace(year=year_now)  # Добавить год
    return result

async def get_session():
    """
    Функция получения сессия для последующего сохранения.
    Returns: Hash сессии, которую необходимо сохранить в файле.
    """
    async with Client(bot_name, api_id=api_id, api_hash=api_hash) as client:
        session_string = await client.export_session_string()
        print(session_string)

async def analyst_tg(service, datas):
    async with Client(
            name=bot_name,
            api_id=api_id,
            api_hash=api_hash,
            session_string=session_string,
            in_memory=True
    ) as client:

        for data in datas:
            date_create = data[0]
            date_from = await convert_time(data[0])
            url_answer = data[1]
            url_split = data[1].split('/')
            print(url_split)

            channel = '@' + url_split[3]
            user_message_id = int(url_split[4])

            print(f"\nConnect {channel}: -------------------> {data[1]}")
            try:
                chat = await client.get_chat(channel)

                dialogy = []
                # Выводим текст последних сообщений
                async for message in client.get_chat_history(chat_id=chat.id, limit=200):
                    message_date = message.date
                    message_id = message.id
                    print(message_id)

                    dialogy.append([message_date, message_text])

                    if user_message_id == message_id:
                        first_author = message.from_user.first_name
                        message_text = message.text
                        break

                comments = dialogy[::-1]

                await rec_data(service, date_create, url_answer, first_author, prompt_trend_gone, comments, message_text)

            except Exception as Ex:
                print(f"Error Ex {Ex}")



async def main_tg():
    datas = [
        ["16.12 09:56:36", "https://telegram.me/proton_chatroom/2241007"],
        ["16.12 07:55:04", "https://telegram.me/VseDengy/1146?comment=46109"]

    ]

    await analyst_tg(datas)


if "__main__" == __name__:
    asyncio.run(main_tg())

#asyncio.run(analyst_tg(['@ru_python_beginners']))

