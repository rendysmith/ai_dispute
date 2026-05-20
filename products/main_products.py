import traceback

from products.sber_polis import main_sber_polis
from products.automir import main_automir

async def main():
    try:
        await main_automir()
    except:
        print('--- Error in AutoMir ---')
        traceback.print_exc()

    try:
        await main_sber_polis()
    except:
        print('--- Error in SberPolis')
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())