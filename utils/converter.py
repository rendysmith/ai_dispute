import re


async def extract_company_name(pattern, url):
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    else:
        return None