from sqlalchemy import create_engine, UUID, Column, Integer, String, Boolean, DateTime, JSON, func
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

class UsersBT24(Base):
    __tablename__ = 'users_bt24'

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    id = Column(String)
    xml_id = Column(String(20))
    active = Column(Boolean)
    name = Column(String)
    last_name = Column(String)
    second_name = Column(String)
    email = Column(String(50))
    # last_login = Column(DateTime(timezone=True))
    # date_register = Column(DateTime(timezone=True))
    # time_zone = Column(String(50))
    # is_online = Column(String(1))
    # time_zone_offset = Column(Integer)
    # timestamp_x = Column(JSON)
    # last_activity_date = Column(JSON)
    # personal_gender = Column(String(1))
    # personal_www = Column(String(255))
    # personal_birthday = Column(DateTime(timezone=True))
    # personal_photo = Column(String(255))
    # personal_mobile = Column(String(20))
    # personal_city = Column(String(50))
    # work_phone = Column(String(20))
    # work_position = Column(String(100))
    # uf_skype_link = Column(String(100))
    # uf_employment_date = Column(DateTime(timezone=True))
    # uf_department = Column(JSON)
    # uf_web_sites = Column(String(255))
    # uf_skype = Column(String(100))
    # uf_usr_1702043059548 = Column(String(100))
    # uf_usr_1719399230907 = Column(String(255))
    # uf_usr_1719399251904 = Column(String(100))
    # uf_usr_1719399278162 = Column(DateTime(timezone=True))
    # uf_usr_1719399314118 = Column(DateTime(timezone=True))
    # user_type = Column(String(50))



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

class HostsZoom(Base):
    __tablename__ = 'hosts_zoom'

    host_id = Column(Integer, primary_key=True, autoincrement=True)
    host = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, index=True)

class Results(Base):
    __tablename__ = 'results'

    result_id = Column(Integer, primary_key=True, autoincrement=True)
    feedback = Column(String, nullable=False, index=True)
    result = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    created_by = Column(String, nullable=False, index=True)
    project = Column(String, nullable=False, index=True)


class TinkoffResults(Base):
    __tablename__ = 'results_tinkoff'

    result_id = Column(Integer, primary_key=True, autoincrement=True)
    result = Column(String, nullable=False, index=True)


class TinkoffHrResults(Base):
    __tablename__ = 'results_tinkoff_hr'

    result_id = Column(Integer, primary_key=True, autoincrement=True)
    result = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    created_by = Column(String, nullable=False, index=True)

class ArticleFunResults(Base):
    __tablename__ = 'results_article_fun'

    result_id = Column(Integer, primary_key=True, autoincrement=True)
    result = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    created_by = Column(String, nullable=False, index=True)

class ArticleEconomyResults(Base):
    __tablename__ = 'results_article_economy'

    result_id = Column(Integer, primary_key=True, autoincrement=True)
    result = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    created_by = Column(String, nullable=False, index=True)

class HoneyBunnyResults(Base):
    __tablename__ = 'results_honeybunny'

    result_id = Column(Integer, primary_key=True, autoincrement=True)
    result = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    created_by = Column(String, nullable=False, index=True)

class WinelabResults(Base):
    __tablename__ = 'results_winelab'

    result_id = Column(Integer, primary_key=True, autoincrement=True)
    feedback = Column(String, nullable=False, index=True)
    result = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    created_by = Column(String, nullable=False, index=True)

class CordiantReviewResults(Base):
    __tablename__ = 'results_cordiant_review'

    result_id = Column(Integer, primary_key=True, autoincrement=True)
    feedback = Column(String, nullable=False, index=True)
    result = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    created_by = Column(String, nullable=False, index=True)

class CordiantReactionResults(Base):
    __tablename__ = 'results_cordiant_reaction'

    result_id = Column(Integer, primary_key=True, autoincrement=True)
    feedback = Column(String, nullable=False, index=True)
    result = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    created_by = Column(String, nullable=False, index=True)

class DatasetArticlePersons(Base):
    __tablename__ = 'dataset_article_persons'

    person_id = Column(Integer, primary_key=True, autoincrement=True)
    fio = Column(String, nullable=False, index=True)
    region = Column(String, nullable=False, index=True)
    sex = Column(String, nullable=False, index=True)
    age = Column(Integer, nullable=False, index=True)
    person_description = Column(String, nullable=False, index=True)
    volume = Column(String, nullable=False, index=True)
    person_guid = Column(UUID(as_uuid=True), default=uuid.uuid4)

class DatasetArticleSubjects(Base):
    __tablename__ = 'dataset_article_subjects'

    subject_id = Column(Integer, primary_key=True, autoincrement=True)
    guid = Column(UUID(as_uuid=True), default=uuid.uuid4)
    fio = Column(String, nullable=False, index=True)

    subject_1 = Column(String, nullable=False, index=True)
    subject_2 = Column(String, nullable=False, index=True)
    subject_3 = Column(String, nullable=False, index=True)
    subject_4 = Column(String, nullable=False, index=True)
    subject_5 = Column(String, nullable=False, index=True)
    subject_6 = Column(String, nullable=False, index=True)
    subject_7 = Column(String, nullable=False, index=True)
    subject_8 = Column(String, nullable=False, index=True)
    subject_9 = Column(String, nullable=False, index=True)
    subject_10 = Column(String, nullable=False, index=True)
    subject_11 = Column(String, nullable=False, index=True)
    subject_12 = Column(String, nullable=False, index=True)
    subject_13 = Column(String, nullable=False, index=True)
    subject_14 = Column(String, nullable=False, index=True)
    subject_15 = Column(String, nullable=False, index=True)
    subject_16 = Column(String, nullable=False, index=True)
    subject_17 = Column(String, nullable=False, index=True)
    subject_18 = Column(String, nullable=False, index=True)
    subject_19 = Column(String, nullable=False, index=True)
    subject_20 = Column(String, nullable=False, index=True)

class ForumRules(Base):
    """
    forum_id: Integer\n
    forum_name: String\n
    forum_rule: String\n
    """
    __tablename__ = 'forum_rules'

    forum_id = Column(Integer, primary_key=True, autoincrement=True)
    forum_name = Column(String, nullable=False, index=True)
    forum_rule = Column(String, nullable=False, index=True)


class Prompt(Base):
    """
    prompt_id: Integer\n
    project_name: String\n
    prompt: String\n
    """
    __tablename__ = 'prompts'

    prompt_id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String, nullable=False, index=True)
    prompt = Column(String, nullable=False, index=True)

class Proxies(Base):
    """
    host_id: Integer\n
    host: String\n
    port: String\n
    """
    __tablename__ = 'proxies'

    host_id = Column(Integer, primary_key=True, autoincrement=True)
    host = Column(String, nullable=False, index=True)
    port = Column(String, nullable=False, index=True)
    login = Column(String, nullable=False, index=True)
    password = Column(String, nullable=False, index=True)
    proxy_type = Column(String, nullable=False, index=True)

class OrgLink(Base):
    """

    """
    __tablename__ = "org_links"
    __table_args__ = {"schema": "double_gis"}

    link_id = Column(Integer, primary_key=True, autoincrement=True)
    link = Column(String, nullable=False, index=True)
    org_link = Column(String, nullable=False, index=True)
    key = Column(String, nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)








