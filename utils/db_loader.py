import logging
import os
from datetime import datetime
from os.path import join, dirname, abspath

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from models.mdl_tables import Base

# Настройка логирования
logger = logging.getLogger(__name__)

current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
current_path = dirname(abspath(__file__))

dotenv_path = join(dirname(dirname(__file__)), '.env')
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
    poolclass=NullPool,
)

SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession
)


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


def _get_model_by_table_name(table_name: str):
    for mapper in Base.registry.mappers:
        if mapper.class_.__tablename__ == table_name:
            return mapper.class_
    return None


async def get_token_credentials(table_name: str, username: str):
    """
    Возвращает api_token и model из таблицы tokens (или другой с колонкой username).

    :param table_name: имя таблицы, например 'tokens'
    :param username: значение в колонке username, например 'chat_gpt'
    :return: (api_token, model) или (False, False)
    """
    model = _get_model_by_table_name(table_name)
    if not model:
        logger.error(f"Table {table_name} not found")
        return False, False

    async with SessionLocal() as session:
        try:
            async with session.begin():
                result = await session.execute(select(model).filter_by(username=username))
                row = result.scalars().first()

                if row:
                    return row.api_token, getattr(row, 'model', None)
                return False, False

        except Exception as Ex:
            logger.error(f"SQL Error Ex: {Ex}")
            return False, False


async def read_universal(session=None, query=None):
    if session:
        result = await session.execute(query)
        return result.scalars().all()
    else:
        async with SessionLocal() as local_session:
            result = await local_session.execute(query)
            return result.scalars().all()
