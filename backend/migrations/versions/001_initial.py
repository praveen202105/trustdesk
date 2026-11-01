"""Initial persistence, immutable source versions and extension."""
from alembic import op
from sqlalchemy import text

import trustdesk.models  # noqa: F401
from trustdesk.db import Base

revision = "001"
down_revision = None

def upgrade():
    op.execute("SELECT pg_advisory_xact_lock(817401)")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind=op.get_bind())
    op.execute(text("CREATE INDEX IF NOT EXISTS ix_documents_fts ON documents USING gin (to_tsvector('english', content))"))

def downgrade():
    raise RuntimeError("Automatic destructive downgrades are intentionally disabled; restore a verified backup")
