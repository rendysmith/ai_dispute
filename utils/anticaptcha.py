import re
from pprint import pprint

import asyncio
import os

from twocaptcha import TwoCaptcha

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')

from dotenv import load_dotenv

load_dotenv(dotenv_path)

captcha_key = os.environ.get("CAPTCHA_KEY")

class SendCaptcha:
    def __init__(self, file_link: str):
        self.file_link = file_link
        self.solver = TwoCaptcha(apiKey=captcha_key, )

    async def normal_captcha(self):
        print('- Send normal captcha...')
        n = 0
        while n < 10:
            result = self.solver.normal(self.file_link)
            print(result)
            if result.get('code'):
                print(result['code'])
                return result['code']

            await asyncio.sleep(1)
            n += 1
            print(f'nN = {n}')

        return None

    async def coordinates_captcha(self):
        print('- Send coordinates captcha...')
        n = 0
        while n < 10:
            result = self.solver.coordinates(self.file_link)
            pprint(result)
            if result.get('code'):
                matches = re.findall(r'x=(\d+),y=(\d+)', result['code'])
                parsed_list = [[int(x), int(y)] for x, y in matches]
                return parsed_list

            await asyncio.sleep(1)
            n += 1
            print(f'nC = {n}')

        return None

async def main():
    anti = SendCaptcha('/home/andrewsmith/PycharmProjects/Sidorin/ai_one_off/downloaded_files/test_smartcaptcha.png')
    result = await anti.coordinates_captcha()
    print(result)

if "__main__" in __name__:
    asyncio.run(main())



