import asyncio
import time

import aiohttp

async def make_request(semaphore, url):
    async with semaphore:
        async with aiohttp.ClientSession() as session:  # Используйте aiohttp для асинхронных запросов
            async with session.get(url) as response:
                await response.text()  # Или response.read() для бинарных данных
                return response.status

async def tst_concurrency(url, n):
    semaphore = asyncio.Semaphore(n)
    tasks = [make_request(semaphore, url) for _ in range(100)] # 100 тестовых запросов
    start_time = time.time()
    results = await asyncio.gather(*tasks)
    end_time = time.time()
    print(f"Concurrency: {n}, Time: {end_time - start_time}, Errors: {sum(1 for status in results if status >= 400)}")

async def main():
    url = "https://example.com"  # Замените на ваш URL
    for n in [1, 5, 10, 20, 50]:
        await tst_concurrency(url, n)

asyncio.run(main())