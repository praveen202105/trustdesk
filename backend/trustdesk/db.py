import re

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


if not re.fullmatch(r"[a-z][a-z0-9_]*", settings.database_schema):
    raise ValueError("Invalid database schema")
engine = create_engine(
    settings.database_url.replace("postgres://", "postgresql+psycopg://", 1).replace(
        "postgresql://", "postgresql+psycopg://", 1
    ),
    pool_pre_ping=True,
    connect_args={
        "connect_timeout": 5,
        "options": "-cstatement_timeout=15000 -clock_timeout=5000 -csearch_path="
        + settings.database_schema
        + ",public",
    },
).execution_options(schema_translate_map={None: settings.database_schema})
SessionLocal = sessionmaker(engine, expire_on_commit=False)
