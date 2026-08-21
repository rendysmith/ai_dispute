import asyncio
import logging

import aiohttp

from sqlalchemy import select, and_, func

from models.mdl_tables import Proxies

from utils.db_loader import read_universal


async def get_one_proxy_from_db(proxy_type=None):
    # 1. Формируем базовый запрос: SELECT * FROM proxies
    query = select(Proxies)

    # 2. Фильтруем только живые прокси
    query = query.filter(Proxies.status != "dead")

    # 3. Обрабатываем фильтр 'mobile'
    if proxy_type:
        filter_condition = and_(
            Proxies.proxy_type == proxy_type,
            Proxies.proxy_type.is_not(None)
        )
        query = query.filter(filter_condition)

    # 4. Случайный выбор одного живого прокси
    query = query.order_by(func.random()).limit(1)

    # 5. Выполняем запрос
    result = await read_universal(query=query)

    # 6. Обрабатываем результат
    if result:
        r_idx = result[0]

        host = r_idx.host
        port = r_idx.port
        login = r_idx.login
        password = r_idx.password

        logging.info(f'--- Proxy data: {host} {port}')
        return host, port, login, password

    else:
        # Если список пуст (result = []), прокси по заданным условиям не найдены.
        logging.warning('--- No proxy found with given filters.')
        return None, None, None, None


async def is_proxy_alive(host, port, login, password):
    """
    Быстрая проверка работоспособности прокси.
    """
    proxy_url = f"http://{login}:{password}@{host}:{port}"
    check_url = "https://api.ipify.org"
    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(check_url, proxy=proxy_url) as response:
                if response.status == 200:
                    return True

    except Exception as e:
        logging.debug(f"Proxy check failed for {host}:{port}: {e}")

    return False


async def get_one_proxy(proxy_type=None):
    """
    Циклически ищет живой прокси в базе данных.
    """
    for attempt in range(10):
        host, port, login, password = await get_one_proxy_from_db(proxy_type)

        if not host:
            return None, None, None, None

        logging.info(f"Checking proxy {host}:{port} (Attempt {attempt + 1})...")

        if await is_proxy_alive(host, port, login, password):
            logging.info(f"Proxy ({proxy_type}) {host}:{port} is ALIVE.")
            return host, port, login, password

        logging.warning(f"Proxy {host}:{port} is DEAD. Retrying...")
        await asyncio.sleep(0.5)

    logging.error("!!! Could not find a valid proxy after multiple attempts.")
    return None, None, None, None
