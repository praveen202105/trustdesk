from alembic import op

from trustdesk.models import Job, Trace

revision = "002"
down_revision = "001"


def upgrade():
    op.execute("SELECT pg_advisory_xact_lock(817401)")
    Job.__table__.create(op.get_bind(), checkfirst=True)
    Trace.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    raise RuntimeError("Use a verified backup; destructive downgrade disabled")
