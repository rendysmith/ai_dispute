from sqlalchemy import create_engine, Column, Integer, String, UUID
from sqlalchemy.orm import sessionmaker, declarative_base
import uuid

Base = declarative_base()

class Users(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, index=True)
    full_name = Column(String, nullable=False, index=True)
    #guid = Column(UUID, nullable=False, index=True)
    guid = Column(UUID(as_uuid=True), default=uuid.uuid4)
    hash_pass = Column(String, nullable=False, index=True)
    position = Column(String, nullable=False, index=True)

class Groups(Base):
    __tablename__ = 'groups'

    group_id = Column(Integer, primary_key=True, autoincrement=True)
    group_name = Column(String, nullable=False, index=True)
    full_name = Column(String, nullable=False, index=True)
    guid = Column(UUID(as_uuid=True), default=uuid.uuid4)

class Roles(Base):
    __tablename__ = 'roles'

    role_id = Column(Integer, primary_key=True, autoincrement=True)
    user_guid = Column(UUID(as_uuid=True))
    group_guid = Column(UUID(as_uuid=True))
    guid = Column(UUID(as_uuid=True), default=uuid.uuid4)

class Tokens(Base):
    __tablename__ = 'tokens'

    token_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, index=True)
    api_token = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, index=True)

class Hosts(Base):
    __tablename__ = 'hosts'

    host_id = Column(Integer, primary_key=True, autoincrement=True)
    host = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, index=True)



