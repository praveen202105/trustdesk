"""Bounded startup readiness and migration entry point; never imports data implicitly."""

import time

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from .db import engine


def main():
    for attempt in range(12):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            break
        except Exception:
            if attempt == 11:
                raise RuntimeError(
                    "Database did not become ready within the bounded startup window"
                ) from None
            time.sleep(2)
    command.upgrade(Config("alembic.ini"), "head")


if __name__ == "__main__":
    main()
