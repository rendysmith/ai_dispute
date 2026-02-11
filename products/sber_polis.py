import asyncio

from utils.constants import empty_blocks
from utils.gs_editor import get_service, read_table_id

from portals.portal_otzovik import blocks_otzovik
from portals.portal_sravni import



async def pars_otzovik(service, project, link, links, min_raiting, max_raiting):
    parsing_blocks = await empty_blocks()

    blocks = await blocks_otzovik(link, parsing_blocks, headless=False)
    print(blocks)

async def pars_sravni(service, project, link, links, min_raiting, max_raiting):
    parsing_blocks = await empty_blocks()
    blocks = await blocks_sravni(link, parsing_blocks, headless=False)





async def main():
    ss_id = '1lVTHhOPynrRk1JKYuBuIapeO7KCTs4Hc95EqGemjUDs'
    project = 'SberInsurance'

    service = await get_service()

    df = await read_table_id(service, ss_id, 'links')
    print(df)

    try:
        df_links = await read_table_id(service, ss_id, project)
        links = df_links['Url'].tolist()
    except:
        links = []

    for idx, row in df.iterrows():
        status =row['status']
        if status == 'OK!':
            continue

        min_raiting = row['min_raiting']
        max_raiting = row['max_raiting']
        link = row['link']

        if 'otzovik' in link:
            status = await pars_otzovik(service, project, link, links, min_raiting, max_raiting)

        elif 'sravni' in link:
            status = await pars_sravni(service, project, link, links, min_raiting, max_raiting)

        print(status)



if "__main__" in __name__:
    asyncio.run(main())



