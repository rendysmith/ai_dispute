import asyncio
from os.path import join, dirname

import requests
import aiohttp
import os
from dotenv import load_dotenv

dotenv_path = join(dirname(dirname(__file__)), '.env')
load_dotenv(dotenv_path)

BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
CHANNEL_ID = os.environ.get("TG_CHANNEL")

async def send_telegram(text: str):
    url = "https://api.telegram.org/bot"
    url += BOT_TOKEN
    method = url + "/sendMessage"

    print(method)

    r = requests.post(method, data={"chat_id": CHANNEL_ID, "text": text})

    if r.status_code != 200:
        raise Exception("post_text error")


async def send_telegram_file(file_path: str, caption: str = None):
    """
    Отправляет файл (фото, видео, документ) в Telegram-канал.
    Автоматически определяет тип файла и использует соответствующий метод Telegram API.
    file_path: Путь к файлу, который нужно отправить.
    caption: Наименование файла в ТГ канале.
    """
    if not os.path.exists(file_path):
        print(f"Ошибка: Файл не найден по пути: {file_path}")
        return

    file_name = os.path.basename(file_path)
    file_extension = os.path.splitext(file_name)[1].lower()

    method_name = ""
    param_name = "" # Имя параметра для файла в запросе (photo, video, document)

    if file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
        method_name = "sendPhoto"
        param_name = "photo"
    elif file_extension in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
        method_name = "sendVideo"
        param_name = "video"
    else:
        method_name = "sendDocument"
        param_name = "document"

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method_name}"

    payload = {"chat_id": CHANNEL_ID}
    if caption:
        payload["caption"] = caption

    try:
        async with aiohttp.ClientSession() as session:
            # Открываем файл для отправки
            with open(file_path, 'rb') as f:
                # aiohttp использует MultipartWriter для отправки файлов
                form = aiohttp.FormData()
                form.add_field("chat_id", str(CHANNEL_ID)) # chat_id должен быть строкой
                form.add_field(param_name, f, filename=file_name, content_type='application/octet-stream')
                if caption:
                    form.add_field("caption", caption)

                async with session.post(url, data=form) as response:
                    response_json = await response.json()
                    if response.status == 200 and response_json.get("ok"):
                        print(f"Файл '{file_name}' успешно отправлен.")
                    else:
                        print(f"Ошибка при отправке файла '{file_name}': {response.status} - {response_json}")
    except aiohttp.ClientError as e:
        print(f"Ошибка соединения при отправке файла '{file_name}': {e}")
    except Exception as e:
        print(f"Непредвиденная ошибка при отправке файла '{file_name}': {e}")

if "__main__" in __name__:
    asyncio.run(send_telegram("test"))
    asyncio.run(send_telegram_file("/home/andrewsmith/PycharmProjects/Sidorin/ai_one_off/downloaded_files/error_screenshot_2025-06-10_17-10-55.png", "Test"))