import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import trustdesk.models  # noqa: F401
from trustdesk.config import settings
from trustdesk.db import Base
from trustdesk.ingest import ingest


@pytest.fixture
def database():
    engine = create_engine(settings.database_url)
    schema = "test_" + uuid.uuid4().hex
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped = engine.execution_options(schema_translate_map={None: schema})
    Base.metadata.create_all(scoped)
    factory = sessionmaker(scoped, expire_on_commit=False)
    with factory.begin() as session:
        ingest(session, Path(__file__).resolve().parents[2] / "capstone/data")
    yield factory
    with engine.begin() as conn:
        conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    engine.dispose()
