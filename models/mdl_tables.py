from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Tokens(Base):
    __tablename__ = 'tokens'

    token_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, index=True)
    api_token = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, index=True)
    model = Column(String, nullable=True, index=True)


class Hosts(Base):
    __tablename__ = 'hosts'

    host_id = Column(Integer, primary_key=True, autoincrement=True)
    host = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, index=True)


class ForumRules(Base):
    """
    forum_id: Integer
    forum_name: String
    forum_rule: String
    """
    __tablename__ = 'forum_rules'

    forum_id = Column(Integer, primary_key=True, autoincrement=True)
    forum_name = Column(String, nullable=False, index=True)
    forum_rule = Column(String, nullable=False, index=True)


class Proxies(Base):
    """
    host_id: Integer
    host: String
    port: String
    """
    __tablename__ = 'proxies'

    host_id = Column(Integer, primary_key=True, autoincrement=True)
    host = Column(String, nullable=False, index=True)
    port = Column(String, nullable=False, index=True)
    login = Column(String, nullable=False, index=True)
    password = Column(String, nullable=False, index=True)
    proxy_type = Column(String, nullable=False, index=True)
    status = Column(String, nullable=True, default=None)
