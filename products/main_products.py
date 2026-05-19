from sber_polis import main_sber_polis
from automir import main_automir

async def main():
    try:
        await main_automir()
    except:
        print('--- Error in AutoMir')

    try:
        await main_sber_polis()
    except:
        print('--- Error in SberPolis')