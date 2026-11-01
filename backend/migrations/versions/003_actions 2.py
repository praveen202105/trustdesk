from alembic import op

from trustdesk.models import Approval, Proposal, ToolCall

revision = "003"
down_revision = "002"
def upgrade():
    op.execute("SELECT pg_advisory_xact_lock(817401)")
    for model in (Proposal, Approval, ToolCall):
        model.__table__.create(op.get_bind(), checkfirst=True)
def downgrade():
    raise RuntimeError("Use a verified backup; destructive downgrade disabled")
