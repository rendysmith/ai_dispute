import asyncio
import os
import re
from pprint import pprint

import requests
from dotenv import load_dotenv
from twocaptcha import TwoCaptcha
from twocaptcha.solver import ApiException, NetworkException

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

captcha_key = os.environ.get("CAPTCHA_KEY")
login_proxy = os.environ.get("LOGIN_PROXY")
pass_proxy = os.environ.get("PASS_PROXY")


def get_captcha_proxy_type():
    raw = os.environ.get("CAPTCHA_PROXY_TYPE", "").strip()
    return raw or None


def get_captcha_servers():
    """
    API-хосты 2captcha (in.php / res.php, не веб-сайт).
    2captcha.com доступен глобально; rucaptcha.com часто отдаёт 403.
    """
    raw = os.environ.get("CAPTCHA_SERVER", "2captcha.com")
    return [s.strip() for s in raw.split(",") if s.strip()]


class ProxyApiClient:
    """ApiClient с прокси и таймаутом для запросов к in.php / res.php."""

    def __init__(self, post_url, proxies=None, timeout=60):
        self.post_url = post_url
        self.proxies = proxies
        self.timeout = timeout

    def in_(self, files=None, **kwargs):
        files = files or {}
        current_url = f"https://{self.post_url}/in.php"
        try:
            if files:
                opened = {key: open(path, "rb") for key, path in files.items()}
                try:
                    resp = requests.post(
                        current_url, data=kwargs, files=opened,
                        proxies=self.proxies, timeout=self.timeout,
                    )
                finally:
                    for f in opened.values():
                        f.close()
            elif "file" in kwargs:
                with open(kwargs.pop("file"), "rb") as f:
                    resp = requests.post(
                        current_url, data=kwargs, files={"file": f},
                        proxies=self.proxies, timeout=self.timeout,
                    )
            else:
                resp = requests.post(
                    current_url, data=kwargs,
                    proxies=self.proxies, timeout=self.timeout,
                )
        except requests.RequestException as exc:
            raise NetworkException(exc) from exc

        if resp.status_code != 200:
            raise NetworkException(f"bad response: {resp.status_code}")

        body = resp.content.decode("utf-8")
        if "ERROR" in body:
            raise ApiException(body)
        return body

    def res(self, **kwargs):
        current_url = f"https://{self.post_url}/res.php"
        try:
            resp = requests.get(
                current_url, params=kwargs,
                proxies=self.proxies, timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise NetworkException(exc) from exc

        if resp.status_code != 200:
            raise NetworkException(f"bad response: {resp.status_code}")

        body = resp.content.decode("utf-8")
        if "ERROR" in body:
            raise ApiException(body)
        return body


async def get_captcha_proxies(proxy_type=None):
    """
    Прокси для API 2captcha — только если через него реально открывается 2captcha.com.
    """
    explicit = os.environ.get("CAPTCHA_PROXY", "").strip()
    if explicit:
        return {"http": explicit, "https": explicit}

    use_proxy = os.environ.get("CAPTCHA_USE_PROXY", "1").lower() in ("1", "true", "yes")
    if not use_proxy:
        return None

    if proxy_type is None:
        proxy_type = get_captcha_proxy_type()

    try:
        from utils.proxy_module import get_one_proxy

        host, port, db_login, db_pass = await get_one_proxy(proxy_type)
        if not host or not port:
            print("--- Captcha: нет прокси с доступом к API 2captcha")
            return None

        login = db_login or login_proxy
        password = db_pass or pass_proxy
        if not login or not password:
            print("--- Captcha: нет логина/пароля для прокси")
            return None

        url = f"http://{login}:{password}@{host}:{port}"
        print(f"--- Captcha API via proxy {host}:{port} (type={proxy_type})")
        return {"http": url, "https": url}

    except Exception as ex:
        print(f"--- Captcha proxy error: {ex}")
        return None


def build_captcha_solver(server: str, proxies=None) -> TwoCaptcha:
    solver = TwoCaptcha(apiKey=captcha_key, server=server)
    solver.api_client = ProxyApiClient(server, proxies=proxies)
    return solver


class SendCaptcha:
    def __init__(self, file_link: str):
        self.file_link = file_link

    async def normal_captcha(self):
        if not captcha_key:
            print("--- CAPTCHA_KEY не задан")
            return None

        print(f"- Send normal captcha... servers={get_captcha_servers()}")

        for proxy_attempt in range(10):
            proxies = await get_captcha_proxies()
            if not proxies:
                print(f"--- Captcha: нет прокси (попытка {proxy_attempt + 1}/10)")
                await asyncio.sleep(1)
                continue

            for server in get_captcha_servers():
                try:
                    solver = build_captcha_solver(server, proxies=proxies)
                    result = solver.normal(self.file_link)
                    if result.get("code"):
                        print(f"+++ Captcha solved via {server}: {result['code']}")
                        return result["code"]
                except NetworkException as ex:
                    print(f"--- {server} network/proxy error: {ex}")
                    break
                except Exception as ex:
                    print(f"--- {server} error: {ex}")

            await asyncio.sleep(1)

        return None

    async def coordinates_captcha(self):
        for proxy_attempt in range(10):
            proxies = await get_captcha_proxies()
            if not proxies:
                await asyncio.sleep(1)
                continue

            for server in get_captcha_servers():
                try:
                    solver = build_captcha_solver(server, proxies=proxies)
                    result = solver.coordinates(self.file_link)
                    pprint(result)
                    if result.get("code"):
                        matches = re.findall(r"x=(\d+),y=(\d+)", result["code"])
                        return [[int(x), int(y)] for x, y in matches]
                except NetworkException as ex:
                    print(f"--- {server} network error: {ex}")
                    break
                except Exception as ex:
                    print(f"--- {server} error: {ex}")

            await asyncio.sleep(1)

        return None


async def main():
    anti = SendCaptcha(
        "/home/andrewsmith/PycharmProjects/Sidorin/ai_one_off/downloaded_files/test_smartcaptcha.png"
    )
    result = await anti.coordinates_captcha()
    print(result)


if "__main__" in __name__:
    asyncio.run(main())
