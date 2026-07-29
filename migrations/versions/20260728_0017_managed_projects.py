"""managed Telegram projects

Revision ID: 20260728_0017
Revises: 20260728_0016
"""
from alembic import op
import sqlalchemy as sa

revision = "20260728_0017"
down_revision = "20260728_0016"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("bot_instances", sa.Column("runtime_mode", sa.String(24), nullable=False, server_default="external"))
    op.add_column("bot_instances", sa.Column("telegram_bot_id", sa.BigInteger()))
    op.add_column("bot_instances", sa.Column("token_encrypted", sa.Text()))
    op.add_column("bot_instances", sa.Column("token_hint", sa.String(32)))
    op.add_column("bot_instances", sa.Column("token_verified_at", sa.DateTime(timezone=True)))
    op.create_index("ix_bot_instances_runtime_mode", "bot_instances", ["runtime_mode"])

def downgrade() -> None:
    op.drop_index("ix_bot_instances_runtime_mode", table_name="bot_instances")
    for name in ("token_verified_at", "token_hint", "token_encrypted", "telegram_bot_id", "runtime_mode"):
        op.drop_column("bot_instances", name)
