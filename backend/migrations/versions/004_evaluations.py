from alembic import op

from trustdesk.models import EvaluationRun

revision = "004"
down_revision = "003"


def upgrade():
    op.execute("SELECT pg_advisory_xact_lock(817401)")
    EvaluationRun.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    raise RuntimeError("Use a verified backup; destructive downgrade disabled")
