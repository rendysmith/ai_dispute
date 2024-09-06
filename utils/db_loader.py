import pandas as pd
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

import os
from os.path import join, dirname, abspath

from dotenv import load_dotenv

from models.mdl_tables import Users, UsersBT24, Groups, Roles, Tokens, Hosts

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

    # tokens_data = session.query(Tokens).all()
    # if tokens_data:
    #     api_tokens = [token.api_token for token in tokens_data]
    #     print(api_tokens)
    #     return api_tokens
    # else:
    #     print("No tokens found")
    #     return None

async def get_hosts():
    async with SessionLocal() as session:
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


async def get_user_bt24(email):
    async with SessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(UsersBT24).filter_by(email=email))
            user_data = result.scalars().first()
            if user_data:
                full_name = f"{user_data.last_name} {user_data.name} {user_data.second_name}"
                return user_data.email, full_name
            else:
                return False, False

    # user_data = session.query(UsersBT24).filter_by(email=email).first()
    # if user_data:
    #     full_name = f"{user_data.last_name} {user_data.name} {user_data.second_name}"
    #     return user_data.email, full_name
    # else:
    #     return False, False

async def get_pass(username):
    async with SessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(Users).filter_by(username=username))
            user_data = result.scalars().first()

            if user_data:
                return user_data.hash_pass, user_data.position
            else:
                return False, False

async def get_user_guid(username):
    async with SessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(Users).filter_by(username=username))
            user_data = result.scalars().first()

            if user_data:
                return user_data.guid
            else:
                return False

async def get_group_guid(group_name):
    async with SessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(Groups).filter_by(group_name=group_name))
            group_data = result.scalars().first()

            if group_data:
                return group_data.guid
            else:
                return False


async def get_role_access(user_guid, group_guid):
    async with SessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(Roles).filter_by(user_guid=user_guid, group_guid=group_guid))
            role_data = result.scalars().first()

            if role_data:
                return role_data.guid
            else:
                return False

async def add_user_to_db(username, full_name, position, hash_pass):
    async with SessionLocal() as session:
        async with session.begin():
            new_user = Users(username=username, full_name=full_name, position=position, hash_pass=hash_pass)
            session.add(new_user)
            await session.commit()

    # new_user = Users(username=username, full_name=full_name, position=position, hash_pass=hash_pass)
    # session.add(new_user)
    # session.commit()
    # session.close()


async def add_data_to_db(datas):
    async with SessionLocal() as session:
        async with session.begin():
            try:
                session.add(datas)
                await session.commit()
                return True, 'Данные успешно добавлены в базу данных.'

            except Exception as Ex:
                await session.rollback()
                return False, Ex


async def add_datas_to_db(table_data, mappings):
    async with SessionLocal() as session:
        async with session.begin():
            try:
                await session.execute(table_data.__table__.delete())
                await session.bulk_insert_mappings(table_data, mappings)
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


async def read_from_postgres_old(table_name: str):
    try:
        # Читаем данные из таблицы в DataFrame
        df = pd.read_sql_table(table_name, con=engine)
        print(type(df))
        return True, df

    except exc.OperationalError as e:
        return False, f"Ошибка подключения к PostgreSQL: {e}"

# async def check_postgres():
#     try:
#         # Подключение к базе данных
#         connection = await asyncpg.connect(
#             database='gener_01',
#             user='postgres',  # Замените на имя вашего пользователя
#             password='D0g#Cat$123!',  # Замените на ваш пароль
#             host='78.155.194.227',  # Замените на адрес вашего сервера базы данных, если он отличается
#             port=5432  # Порт по умолчанию для PostgreSQL
#         )
#
#         # Выполнение SQL-запроса
#         result = await connection.fetch("SELECT version();")
#         db_version = result[0][0]
#         print("Версия сервера PostgreSQL:", db_version)
#
#         # Закрытие соединения с базой данных
#         await connection.close()
#
#     except asyncpg.exceptions.PostgresError as e:
#         print("Ошибка при подключении к базе данных:", e)

# async def check_postgres_connection():
#     try:
#         # Замените параметры подключения на свои
#         connection = await asyncpg.connect(user=DB_USERNAME,
#                                            password=DB_PASSWORD,
#                                            database=DB_NAME,
#                                            host=DB_HOST,
#                                            port=DB_PORT)
#         await connection.close()
#         return True
#
#     except asyncpg.exceptions.InvalidPasswordError:
#         print("Ошибка: Неверный пароль")
#
#     except asyncpg.exceptions.InvalidCatalogNameError:
#         print("Ошибка: Неверное имя базы данных")
#
#     except asyncpg.exceptions.ClientCannotConnectError:
#         print("Ошибка: Не удалось подключиться к серверу")
#
#     except Exception as e:
#         print(f"Ошибка: {e}")
#     return False

# async def check_postgres_connection_sqlal():
#     try:
#         url = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
#         print(url)
#         engine = create_engine(url)
#         async with engine.connect():
#             return True
#     except exc.OperationalError as e:
#         print(f"Ошибка подключения к PostgreSQL: {e}")

# async def main():
#     print('******************************************************')
#     await check_postgres()
#
#     print('******************************************************')
#     connected = await check_postgres_connection()
#     if connected:
#         print("\n---------1---------\nУспешное подключение к PostgreSQL")
#     else:
#         print("\n---------1---------\nНе удалось подключиться к PostgreSQL")
#
#     print('******************************************************')
#     connected = await check_postgres_connection_sqlal()
#     if connected:
#         print("\n---------2---------\nУспешное подключение к PostgreSQL")
#     else:
#         print("\n----------2--------\nНе удалось подключиться к PostgreSQL")