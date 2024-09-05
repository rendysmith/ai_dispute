import asyncio
import random

from datetime import datetime, timedelta

import zlib
import base64

from utils.gs_editor import pars_url
from utils.ai_module import generate_and_white
from utils.user_agent import get_playwright

import os
from dotenv import load_dotenv

current_date = datetime.now()

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

days_ago = int(os.environ.get("DAYS_AGO"))
max_sec = int(os.environ.get("MAX_SEC"))

async def compress_string(input_string):
    # Сжимаем строку с помощью zlib
    compressed_data = zlib.compress(input_string.encode('utf-8'))
    # Кодируем сжатые данные в Base64 для удобства хранения и передачи
    compressed_base64 = base64.b64encode(compressed_data)
    return compressed_base64.decode('utf-8')

async def decompress_string(compressed_string):
    # Декодируем данные из Base64
    compressed_data = base64.b64decode(compressed_string.encode('utf-8'))
    # Распаковываем данные с помощью zlib
    decompressed_data = zlib.decompress(compressed_data)
    return decompressed_data.decode('utf-8')

async def convert_date(month):
    months = {
        'января': 1,
        'февраля': 2,
        "марта": 3,
        "апреля": 4,
        "мая": 5,
        "июня": 6,
        "июля": 7,
        "августа": 8,
        "сентября": 9,
        "октября": 10,
        "ноября": 11,
        "декабря": 12
    }
    return months[month]

async def check_2gis(service, url, pattern, criteria, ss_id, project):
    playwright, browser, page = await get_playwright(url)

    ts = random.randint(5, max_sec)
    print(f'Wait {ts} sec...')
    await asyncio.sleep(ts)

    links = await pars_url(service, ss_id, project)

    blocks = await page.query_selector_all('div[class="_11gvyqv"]')
    #print(len(blocks))

    for block in blocks:
        date_content = await block.query_selector('div[class="_4mwq3d"]')
        date = await date_content.inner_text()
        date = date.split(', ')[0].split(' ')
        print(date)

        year = int(date[2])
        month = await convert_date(date[1])
        day = int(date[0])

        target_date = datetime(year, month, day)
        formatted_date = target_date.strftime("%d.%m.%Y")
        print(formatted_date)

        if (current_date - target_date) > timedelta(days=days_ago):
            print(f'--- Отзыв старше {days_ago} дней = {date}.')
            continue

        try:
            answer_content = block.query_selector('div[class="_sgs1pz"]')
            answer = answer_content.inner_text()
            print('Уже есть ответ на комментарий')
            continue

        except:
            pass

        author_content = await block.query_selector('span[class="_16s5yj36"]')
        author = await author_content.inner_text()
        author = author.strip()
        print('\n', author)

        feedback_content = await block.query_selector('div[class="_49x36f"]')
        feedback = await feedback_content.inner_text()
        print(feedback)

        url_answer = await compress_string(feedback)

        if url_answer in links:
            print('Такой комментарий уже есть в списке')
            continue

        author = f"{author}\n{url}"

        await generate_and_white(service=service,
                                 url_answer=url_answer,
                                 author=author,
                                 formatted_date=formatted_date,
                                 ss_id=ss_id,
                                 project=project,
                                 feedback=feedback,
                                 pattern=pattern,
                                 criteria=criteria)

    await browser.close()
    await playwright.stop()
#
# if __name__ == '__main__':
#     url = 'https://catalog.api.2gis.ru/3.0/items/byid?id=1830223003790126&key=rurbbn3446&locale=ru_RU&fields=items.locale,items.flags,search_attributes,items.adm_div,items.city_alias,items.region_id,items.segment_id,items.reviews,items.point,request_type,context_rubrics,query_context,items.links,items.name_ex,items.name_back,items.org,items.group,items.dates,items.external_content,items.contact_groups,items.comment,items.ads.options,items.email_for_sending.allowed,items.stat,items.stop_factors,items.description,items.geometry.centroid,items.geometry.selection,items.geometry.style,items.timezone_offset,items.context,items.level_count,items.address,items.is_paid,items.access,items.access_comment,items.for_trucks,items.is_incentive,items.paving_type,items.capacity,items.schedule,items.floors,ad,items.rubrics,items.routes,items.platforms,items.directions,items.barrier,items.reply_rate,items.purpose,items.purpose_code,items.attribute_groups,items.route_logo,items.has_goods,items.has_apartments_info,items.has_pinned_goods,items.has_realty,items.has_exchange,items.has_payments,items.has_dynamic_congestion,items.is_promoted,items.congestion,items.delivery,items.order_with_cart,search_type,items.has_discount,items.metarubrics,items.detailed_subtype,items.temporary_unavailable_atm_services,items.poi_category,items.structure_info.material,items.structure_info.floor_type,items.structure_info.gas_type,items.structure_info.year_of_construction,items.structure_info.elevators_count,items.structure_info.is_in_emergency_state,items.structure_info.project_type&viewpoint1=65.54303807368548,57.14851552124055&viewpoint2=65.56844392631452,57.14303247875946&stat[sid]=90fd004f-822f-480f-87ea-04d1021fba6b&stat[user]=dca766d0-ecc2-413a-98e9-94b16464ace1&shv=2024-08-01-20&r=2268910760'
#     url = 'https://catalog.api.2gis.ru/3.0/items/byid?id=70000001021399041&key=rurbbn3446&locale=ru_RU&fields=items.locale,items.flags,search_attributes,items.adm_div,items.city_alias,items.region_id,items.segment_id,items.reviews,items.point,request_type,context_rubrics,query_context,items.links,items.name_ex,items.name_back,items.org,items.group,items.dates,items.external_content,items.contact_groups,items.comment,items.ads.options,items.email_for_sending.allowed,items.stat,items.stop_factors,items.description,items.geometry.centroid,items.geometry.selection,items.geometry.style,items.timezone_offset,items.context,items.level_count,items.address,items.is_paid,items.access,items.access_comment,items.for_trucks,items.is_incentive,items.paving_type,items.capacity,items.schedule,items.floors,ad,items.rubrics,items.routes,items.platforms,items.directions,items.barrier,items.reply_rate,items.purpose,items.purpose_code,items.attribute_groups,items.route_logo,items.has_goods,items.has_apartments_info,items.has_pinned_goods,items.has_realty,items.has_exchange,items.has_payments,items.has_dynamic_congestion,items.is_promoted,items.congestion,items.delivery,items.order_with_cart,search_type,items.has_discount,items.metarubrics,items.detailed_subtype,items.temporary_unavailable_atm_services,items.poi_category,items.structure_info.material,items.structure_info.floor_type,items.structure_info.gas_type,items.structure_info.year_of_construction,items.structure_info.elevators_count,items.structure_info.is_in_emergency_state,items.structure_info.project_type&stat[sid]=90fd004f-822f-480f-87ea-04d1021fba6b&stat[user]=dca766d0-ecc2-413a-98e9-94b16464ace1&shv=2024-08-01-20&r=2257662115'
#     url = 'https://catalog.api.2gis.ru/3.0/items/byid?id=1830115629597637&key=rurbbn3446&locale=ru_RU&fields=items.locale,items.flags,search_attributes,items.adm_div,items.city_alias,items.region_id,items.segment_id,items.reviews,items.point,request_type,context_rubrics,query_context,items.links,items.name_ex,items.name_back,items.org,items.group,items.dates,items.external_content,items.contact_groups,items.comment,items.ads.options,items.email_for_sending.allowed,items.stat,items.stop_factors,items.description,items.geometry.centroid,items.geometry.selection,items.geometry.style,items.timezone_offset,items.context,items.level_count,items.address,items.is_paid,items.access,items.access_comment,items.for_trucks,items.is_incentive,items.paving_type,items.capacity,items.schedule,items.floors,ad,items.rubrics,items.routes,items.platforms,items.directions,items.barrier,items.reply_rate,items.purpose,items.purpose_code,items.attribute_groups,items.route_logo,items.has_goods,items.has_apartments_info,items.has_pinned_goods,items.has_realty,items.has_exchange,items.has_payments,items.has_dynamic_congestion,items.is_promoted,items.congestion,items.delivery,items.order_with_cart,search_type,items.has_discount,items.metarubrics,items.detailed_subtype,items.temporary_unavailable_atm_services,items.poi_category,items.structure_info.material,items.structure_info.floor_type,items.structure_info.gas_type,items.structure_info.year_of_construction,items.structure_info.elevators_count,items.structure_info.is_in_emergency_state,items.structure_info.project_type&viewpoint1=65.54303807368548,57.14851552124055&viewpoint2=65.56844392631452,57.14303247875946&stat[sid]=90fd004f-822f-480f-87ea-04d1021fba6b&stat[user]=dca766d0-ecc2-413a-98e9-94b16464ace1&shv=2024-08-01-20&r=1780554466'
#
