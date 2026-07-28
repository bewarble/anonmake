"""project operational state

Revision ID: 20260728_0016
Revises: 20260728_0015
"""
from alembic import op
import sqlalchemy as sa

revision = "20260728_0016"
down_revision = "20260728_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bot_instances", sa.Column("is_maintenance", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("bot_instances", sa.Column("maintenance_message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("bot_instances", "maintenance_message")
    op.drop_column("bot_instances", "is_maintenance")
