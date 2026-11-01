from alembic import context

import trustdesk.models  # noqa: F401
from trustdesk.config import settings
from trustdesk.db import Base, engine


def run_migrations():
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata, version_table_schema=settings.database_schema)
        with context.begin_transaction():
            context.run_migrations()

run_migrations()
