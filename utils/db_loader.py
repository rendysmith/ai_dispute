from venv import logger

import pandas as pd
from datetime import datetime

from sqlalchemy import text, update, insert, inspect
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

import os
from os.path import join, dirname, abspath

from dotenv import load_dotenv

from models.mdl_tables import Users, UsersBT24, Groups, Roles, Tokens, Hosts, Base

import logging

# Настройка логирования
logger = logging.getLogger(__name__)

current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
current_path = dirname(abspath(__file__))

dotenv_path = join(dirname(dirname(__file__)), '.env')
#print(dotenv_path)
# print('Размести .env тут', dirname(dirname(__file__)))
load_dotenv(dotenv_path)

def pool_conn():
    host = os.environ.get("POSTGRESQL_HOST")
    port = os.environ.get("POSTGRESQL_PORT")
    database = os.environ.get("POSTGRESQL_DB")
    user = os.environ.get("POSTGRESQL_USERNAME")
    password = os.environ.get("POSTGRESQL_PASSWORD")
    DATABASE_URL = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
    return DATABASE_URL

engine = create_async_engine(
    pool_conn(),
    pool_size=2,  # Максимальное количество постоянных соединений
    max_overflow=5,  # Максимальное количество "лишних" соединений
)

SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession
)

async def get_api_tokens():
    async with SessionLocal() as session:
        try:
            async with session.begin():
                result = await session.execute(select(Tokens))
                tokens_data = result.scalars().all()

                if tokens_data:
                    api_tokens = [token.api_token for token in tokens_data]
                    print(api_tokens)
                    return api_tokens
                else:
                    print("No tokens found")
                    return None

        except Exception as Ex:
            logger.error(f"SQL Error Ex: {Ex}")
            return False

async def get_hosts():
    async with SessionLocal() as session:
        try:
            async with session.begin():
                try:
                    result = await session.execute(select(Hosts).filter_by(status="free"))
                    hosts_data = result.scalars().all()
                except Exception as Ex:
                    print((Ex))
                    return None

                if hosts_data:
                    hosts = [host.host for host in hosts_data]
                    print(hosts)
                    return hosts
                else:
                    print("No hosts found")
                    return None

        except Exception as Ex:
            logger.error(f"SQL Error Ex: {Ex}")
            return False

async def get_user_bt24(email):
    async with SessionLocal() as session:
        try:
            async with session.begin():
                result = await session.execute(select(UsersBT24).filter_by(email=email))
                user_data = result.scalars().first()
                if user_data:
                    full_name = f"{user_data.last_name} {user_data.name} {user_data.second_name}"
                    return user_data.email, full_name

                else:
                    return False, False

        except Exception as Ex:
            logger.error(f"SQL Error Ex: {Ex}")
            return False, False

async def get_pass(username):
    async with SessionLocal() as session:
        try:
            async with session.begin():
                result = await session.execute(select(Users).filter_by(username=username))
                user_data = result.scalars().first()

                if user_data:
                    return user_data.hash_pass, user_data.position
                else:
                    return False, False

        except Exception as Ex:
            logger.error(f"SQL Error Ex: {Ex}")
            return False, False

async def get_user_guid(username):
    async with SessionLocal() as session:
        try:
            async with session.begin():
                result = await session.execute(select(Users).filter_by(username=username))
                user_data = result.scalars().first()

                if user_data:
                    return user_data.guid
                else:
                    return False

        except Exception as Ex:
            logger.error(f"SQL Error Ex: {Ex}")
            return False

async def get_group_guid(group_name):
    async with SessionLocal() as session:
        try:
            async with session.begin():
                result = await session.execute(select(Groups).filter_by(group_name=group_name))
                group_data = result.scalars().first()

                if group_data:
                    return group_data.guid
                else:
                    return False

        except Exception as Ex:
            logger.error(f"SQL Error Ex: {Ex}")
            return False

async def get_role_access(user_guid, group_guid):
    async with SessionLocal() as session:
        try:
            async with session.begin():
                result = await session.execute(select(Roles).filter_by(user_guid=user_guid, group_guid=group_guid))
                role_data = result.scalars().first()

                if role_data:
                    return role_data.guid
                else:
                    return False

        except Exception as Ex:
            logger.error(f"SQL Error Ex: {Ex}")
            return False

async def add_user_to_db(username, full_name, position, hash_pass):
    async with SessionLocal() as session:
        try:
            async with session.begin():
                new_user = Users(username=username, full_name=full_name, position=position, hash_pass=hash_pass)
                session.add(new_user)
                await session.commit()

        except Exception as Ex:
            logger.error(f"SQL Error Ex: {Ex}")
            return False

async def add_data_to_db(datas):
    async with SessionLocal() as session:
        try:
            async with session.begin():
                try:
                    session.add(datas)
                    await session.commit()
                    return True, 'Данные успешно добавлены в базу данных.'

                except Exception as Ex:
                    await session.rollback()
                    return False, Ex

        except Exception as Ex:
            logger.error(f"SQL Error Ex: {Ex}")
            return False, False


async def add_datas_to_db(table_data, mappings):
    async with SessionLocal() as session:
        try:
            # Создаем оператор INSERT для массовой вставки
            stmt = insert(table_data).values(mappings)

            # Выполняем асинхронно
            await session.execute(stmt)
            await session.commit()
            return True
        except Exception as Ex:
            await session.rollback()
            return Ex

async def add_data_to_db_by_filter(table_data, where_data, value_data, datas):
    async with SessionLocal() as session:
        async with session.begin():
            try:
                # Check if forum_name already exists
                existing_rule = await session.execute(
                    select(table_data).where(where_data)
                )
                existing_rule = existing_rule.scalars().first()

                if existing_rule:
                    # Update existing rule
                    await session.execute(
                        update(table_data)
                        .where(where_data)
                        .values(value_data)
                    )
                    await session.commit()
                    return True, 'Правило форума успешно обновлено.'
                else:
                    # Add new rule
                    session.add(datas)
                    await session.commit()
                    return True, 'Данные успешно добавлены в базу данных.'

            except Exception as Ex:
                await session.rollback()
                return False, Ex

async def read_data_from_db(table_data, limit, page):
    async with SessionLocal() as session:
        try:
            query = select(table_data).limit(limit).offset((page - 1) * limit)
            result = await session.execute(query)
            results = result.scalars().all()
            return True, results

        except Exception as Ex:
            return False, Ex

async def read_data_from_db_filter(table_data, **filter):
    async with SessionLocal() as session:
        try:
            result = await session.execute(select(table_data).filter_by(**filter))
            results = result.scalars().all()
            return True, results

        except Exception as Ex:
            return False, Ex

async def read_data_from_db_filter_limit(table_data, limit, page, **filter):
    async with SessionLocal() as session:
        try:
            query = select(table_data).limit(limit).offset((page - 1) * limit).filter_by(**filter)
            result = await session.execute(query)
            results = result.scalars().all()
            return True, results

        except Exception as Ex:
            return False, Ex

async def write_to_postgres(df, table_name: str):
    try:
        # Записываем новые данные в таблицу
        df.to_sql(table_name, con=engine, if_exists='replace', index=False)
        return True, 'OK!'

    except Exception as Ex:
        return False, f"Ошибка подключения к PostgreSQL: {Ex}"

async def append_to_postgres_results(df, table_name: str):
    """
    :param df: DataFrame data
    :param table_name: DB table name
    :return:
    """
    try:
        async with SessionLocal() as session:
            async with session.begin():
                # Создаем SQL запрос для вставки данных
                columns = ', '.join(df.columns)
                values = ', '.join([':' + col for col in df.columns])
                insert_stmt = f"INSERT INTO {table_name} ({columns}) VALUES ({values})"

                # Выполняем вставку для каждой строки DataFrame
                for _, row in df.iterrows():
                    await session.execute(text(insert_stmt), row.to_dict())

                await session.commit()
        return True, 'OK!'

    except Exception as Ex:
        return False, f"Ошибка подключения к PostgreSQL: {Ex}"

async def read_from_postgres(table_name: str):
    async with SessionLocal() as session:
        try:
            query = text(f"SELECT * FROM {table_name}")

            # Выполняем запрос
            result = await session.execute(query)

            # Получаем данные и названия столбцов
            data = result.fetchall()
            column_names = result.keys()

            # Создаем pandas DataFrame
            df = pd.DataFrame(data, columns=column_names)
            return True, df

        except Exception as Ee:
            return False, f"Ошибка подключения к PostgreSQL: {Ee}"

async def read_data_from_db_filter_limit_universal(table_name: str, limit, page, filters=None):
    """
    :param table_name: name of table STR
    :param limit:
    :param page:
    :param filters:
    :return:
    """
    async with SessionLocal() as session:
        try:
            for mapper in Base.registry.mappers:
                if mapper.class_.__tablename__ == table_name:
                    model = mapper.class_
                    break

            query = select(model).limit(limit).offset((page - 1) * limit)

            print(f"filters: {type(filters)}")
            print(f"filters: {filters}" )
            if filters:
                query = query.filter(filters)

            result = await session.execute(query)
            results = result.scalars().all()
            return True, results

        except Exception as Ex:
            return False, Ex

async def add_data_to_db_universal(datas):
    table_name = datas.table_name
    data_dict = datas.datas

    async with SessionLocal() as session:
        async with session.begin():
            try:
                model = None
                for mapper in Base.registry.mappers:
                    if mapper.class_.__tablename__ == table_name:
                        model = mapper.class_
                        break

                if not model:
                    txt =  f"Таблица {table_name} не найдена"
                    #print(txt)
                    True, txt

                    # Проверка полей
                for field in data_dict.keys():
                    if not hasattr(model, field):
                        txt = f"Поле {field} не существует в таблице {table_name}"
                        #print(txt)
                        True, txt

                #print("Model:", model)
                _datas_ = model(**data_dict)
                #print("_datas_:", _datas_)

                session.add(_datas_)
                await session.commit()
                return True, 'Данные успешно добавлены в базу данных.'

            except Exception as Ex:
                await session.rollback()
                return False, Ex

async def delete_data_from_db_universal(datas):
    table_name = datas.table_name
    position = datas.position

    async with SessionLocal() as session:
        try:
            model = None
            for mapper in Base.registry.mappers:
                if mapper.class_.__tablename__ == table_name:
                    model = mapper.class_
                    break

            if not model:
                txt_m = "Таблица languages не найдена в моделях"
                return False, txt_m

            # 2. Ищем запись для удаления
            record = await session.get(model, position)
            if not record:
                txt_r =  f"Запись с ID {position} не найдена"
                return False, txt_r

            # 3. Удаляем запись
            await session.delete(record)
            await session.commit()

            txt_result = f"Запись с ID {position} успешно удалена"
            return True, txt_result

        except Exception as Ex:
            return False, str(Ex)

async def update_data_from_db_universal(datas):
    table_name = datas.table_name
    column = datas.column
    position = datas.position
    new_data = datas.new_data

    async with SessionLocal() as session:
        async with session.begin():
            try:
                # 1. Находим модель таблицы
                model = None
                for mapper in Base.registry.mappers:
                    if mapper.class_.__tablename__ == table_name:
                        model = mapper.class_
                        break

                if not model:
                    txt_m = f"Таблица {table_name} не найдена"
                    return False, txt_m

                # 2. Проверяем существование колонки
                if not hasattr(model, column):
                    txt_h = f"Колонка {column} не существует в таблице {table_name}"
                    return False, txt_h

                # 3. Получаем запись
                record = await session.get(model, position)
                if not record:
                    txt_r = f"Запись с ID {position} не найдена"
                    return False, txt_r

                # 4. Проверяем, что колонка не является первичным ключом
                primary_keys = [pk.name for pk in inspect(model).primary_key]
                if column in primary_keys:
                    txt_c = "Нельзя изменять первичный ключ"
                    return False, txt_c

                # 5. Обновляем значение
                setattr(record, column, new_data)
                session.add(record)
                await session.commit()
                return True, "Значение успешно обновлено"

            except ValueError as ve:
                await session.rollback()
                return False, str(ve)

            except Exception as e:
                await session.rollback()
                return False, f"Ошибка при обновлении: {str(e)}"

async def get_and_lock_row(session, table_data, filters=None):
    query = (
        select(table_data)
        .order_by(table_data.link_id)
        .with_for_update(skip_locked=True)
        .limit(1)
    )

    if filters is not None:
        query = query.where(filters)

    result = await session.execute(query)
    row = result.scalar_one_or_none()
    return row

async def update_universal(session, query):
    await session.execute(query)
    await session.commit()

async def read_universal(session, query):
    result = await session.execute(query)
    return result.scalars().all()



