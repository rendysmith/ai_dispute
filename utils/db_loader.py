import pandas as pd
from datetime import datetime

from sqlalchemy import create_engine, MetaData, text, exc
from sqlalchemy.pool import QueuePool  # Импортируем QueuePool для создания пула соединений
from sqlalchemy.orm import sessionmaker

import os
from os.path import join, dirname, abspath

import asyncpg
from asyncpg.pool import Pool

import asyncio
from dotenv import load_dotenv

from models.mdl_tables import Base, Users, Groups, Roles, Tokens, Hosts

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
    DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    return DATABASE_URL

engine = create_engine(
    pool_conn(),
    poolclass=QueuePool,  # Указываем класс для создания пула соединений
    pool_size=5,  # Количество соединений в пуле (по умолчанию 5)
    max_overflow=10,  # Максимальное количество "лишних" соединений, которые могут быть созданы (по умолчанию 10)
)

Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
session = SessionLocal()

async def get_api_tokens():
    tokens_data = session.query(Tokens).all()
    if tokens_data:
        api_tokens = [token.api_token for token in tokens_data]
        print(api_tokens)
        return api_tokens
    else:
        print("No tokens found")
        return None

async def get_hosts():
    hosts_data = session.query(Hosts).filter_by(status='free').all()
    if hosts_data:
        hosts = [host.host for host in hosts_data]
        print(hosts)
        return hosts
    else:
        print("No hosts found")
        return None

async def get_pass(username):
    user_data = session.query(Users).filter_by(username=username).first()
    if user_data:
        return user_data.hash_pass, user_data.position
    else:
        return False, False

async def get_user_guid(username):
    user_data = session.query(Users).filter_by(username=username).first()
    if user_data:
        return user_data.guid
    else:
        return False

async def get_group_guid(group_name):
    group_data = session.query(Groups).filter_by(group_name=group_name).first()
    if group_data:
        return group_data.guid
    else:
        return False

async def get_role_access(user_guid, group_guid):
    role_data = session.query(Roles).filter_by(user_guid=user_guid, group_guid=group_guid).first()
    if role_data:
        return role_data.guid
    else:
        return False

async def add_user_to_db(username, full_name, position, hash_pass):
    new_user = Users(username=username, full_name=full_name, position=position, hash_pass=hash_pass)
    session.add(new_user)
    session.commit()
    session.close()

async def write_to_postgres(df, table_name: str):
    try:
        #url = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        #engine = create_engine(url)

        # Записываем новые данные в таблицу
        df.to_sql(table_name, con=engine, if_exists='replace', index=False)
        return True, 'OK!'

    except exc.OperationalError as e:
        return False, f"Ошибка подключения к PostgreSQL: {e}"

async def read_from_postgres(table_name: str):
    try:
        #url = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        #engine = create_engine(url)

        # Читаем данные из таблицы в DataFrame
        df = pd.read_sql_table(table_name, con=engine)
        print(type(df))
        return True, df

    except exc.OperationalError as e:
        return False, f"Ошибка подключения к PostgreSQL: {e}"

async def check_postgres():
    try:
        # Подключение к базе данных
        connection = await asyncpg.connect(
            database='gener_01',
            user='postgres',  # Замените на имя вашего пользователя
            password='D0g#Cat$123!',  # Замените на ваш пароль
            host='78.155.194.227',  # Замените на адрес вашего сервера базы данных, если он отличается
            port=5432  # Порт по умолчанию для PostgreSQL
        )

        # Выполнение SQL-запроса
        result = await connection.fetch("SELECT version();")
        db_version = result[0][0]
        print("Версия сервера PostgreSQL:", db_version)

        # Закрытие соединения с базой данных
        await connection.close()

    except asyncpg.exceptions.PostgresError as e:
        print("Ошибка при подключении к базе данных:", e)

async def check_postgres_connection():
    try:
        # Замените параметры подключения на свои
        connection = await asyncpg.connect(user=DB_USERNAME,
                                           password=DB_PASSWORD,
                                           database=DB_NAME,
                                           host=DB_HOST,
                                           port=DB_PORT)
        await connection.close()
        return True

    except asyncpg.exceptions.InvalidPasswordError:
        print("Ошибка: Неверный пароль")

    except asyncpg.exceptions.InvalidCatalogNameError:
        print("Ошибка: Неверное имя базы данных")

    except asyncpg.exceptions.ClientCannotConnectError:
        print("Ошибка: Не удалось подключиться к серверу")

    except Exception as e:
        print(f"Ошибка: {e}")
    return False

async def check_postgres_connection_sqlal():
    try:
        url = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        print(url)
        engine = create_engine(url)
        async with engine.connect():
            return True
    except exc.OperationalError as e:
        print(f"Ошибка подключения к PostgreSQL: {e}")

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