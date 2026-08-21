import asyncio
import os
import time

from dotenv import load_dotenv

from utils.anticaptcha import SendCaptcha
from utils.central_module import wait_for_portal
from utils.constants import months

corn_folder = os.path.dirname(os.path.dirname(__file__))

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)
max_sec = int(os.environ.get("MAX_SEC"))
captcha_key = os.environ.get("CAPTCHA_KEY")


async def date_convert(date_str):
    parts = date_str.split()
    date = 'Не определено'
    if len(parts) == 3:
        day = parts[0].zfill(2)
        month_value = months.get(parts[1].lower(), '00')
        month = str(month_value).zfill(2)
        year = parts[2]
        date = f"{day}.{month}.{year}"

    return date


async def _solve_recaptcha_pw(page) -> bool:
    if not captcha_key:
        return False

    try:
        from playwright_captcha import TwoCaptchaSolver, CaptchaType, FrameworkType
        from twocaptcha import AsyncTwoCaptcha
    except ImportError:
        print('--- playwright_captcha not installed')
        return False

    from utils.anticaptcha import get_captcha_servers

    for server in get_captcha_servers():
        try:
            captcha_client = AsyncTwoCaptcha(captcha_key, server=server)
            async with TwoCaptchaSolver(
                framework=FrameworkType.PLAYWRIGHT,
                page=page,
                async_two_captcha_client=captcha_client,
            ) as solver:
                await solver.solve_captcha(
                    captcha_container=page,
                    captcha_type=CaptchaType.RECAPTCHA_V2,
                )
            return True
        except Exception as ex:
            print(f'--- reCAPTCHA solve error ({server}): {ex}')

    return False


async def _captcha_image_present(page) -> bool:
    if await page.locator('img#captcha-img').count() > 0:
        return True

    input_el = await page.query_selector('input[type="text"]')
    if not input_el:
        return False

    imgs = await page.query_selector_all('img[src]')
    return len(imgs) == 1


async def solve_captcha_pw(page) -> bool:
    """Решение капчи Otzovik через 2captcha (Playwright)."""
    if not captcha_key:
        print('--- CAPTCHA_KEY не задан')
        return False

    for attempt in range(10):
        if not await _captcha_image_present(page):
            recaptcha_frame = await page.locator('iframe[src*="recaptcha"]').count()
            if recaptcha_frame > 0:
                print('--- reCAPTCHA detected')
                if await _solve_recaptcha_pw(page):
                    await page.wait_for_timeout(3000)
                    if not await _captcha_image_present(page):
                        print('+++ reCAPTCHA solved')
                        return True
            else:
                print('--- No captcha')
                return True

        print(f'>>> Captcha found, solving... (attempt {attempt + 1})')

        captcha_img = await page.query_selector('img#captcha-img')
        if not captcha_img:
            imgs = await page.query_selector_all('img[src]')
            if len(imgs) == 1:
                captcha_img = imgs[0]

        if not captcha_img:
            return False

        temp_path = os.path.join(corn_folder, 'temp')
        os.makedirs(temp_path, exist_ok=True)
        file_link = os.path.join(temp_path, f'captcha_image_{int(time.time())}.png')
        await captcha_img.screenshot(path=file_link)
        print(f'-- Captcha screenshot: {file_link}')

        capcha_text = await sent_captcha(file_link)
        if os.path.exists(file_link):
            os.remove(file_link)

        if not capcha_text:
            print('--- 2captcha не вернул ответ')
            await page.reload(wait_until='domcontentloaded')
            await wait_for_portal()
            continue

        input_captcha = await page.query_selector('input[type="text"]')
        if not input_captcha:
            return False

        await input_captcha.fill(capcha_text)
        await asyncio.sleep(1)
        await input_captcha.press('Enter')
        await page.wait_for_timeout(3000)

        if not await _captcha_image_present(page):
            print('+++ Captcha solved')
            return True

        print('--- Captcha still present, retry...')
        await page.reload(wait_until='domcontentloaded')
        await wait_for_portal()

    return False


async def check_captcha(page):
    return await solve_captcha_pw(page)


async def sent_captcha(file_link):
    print('--- Send captcha...')
    anti = SendCaptcha(file_link)
    return await anti.normal_captcha()


async def get_feedback(page, url):
    await page.goto(url)

    status = await check_captcha(page)
    if status == False:
        return None

    text = await page.locator('div.item-right').inner_text()
    await asyncio.sleep(2)
    return text
