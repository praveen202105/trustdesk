from alembic import context
from sqlalchemy import text

import trustdesk.models  # noqa: F401
from trustdesk.config import settings
from trustdesk.db import Base, engine


def run_migrations():
    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(817401)"))
        context.configure(
            connection=connection,
            target_metadata=Base.metadata,
            version_table_schema=settings.database_schema,
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations()
