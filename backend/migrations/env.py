from alembic import context

import trustdesk.models  # noqa: F401
from trustdesk.db import Base, engine


def run_migrations():
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()

run_migrations()
