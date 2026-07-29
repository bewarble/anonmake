"""use bigint for Telegram bot IDs in project drafts

Revision ID: 20260729_0019
Revises: 20260728_0018
"""

from alembic import op
import sqlalchemy as sa


revision = "20260729_0019"
down_revision = "20260728_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "project_setup_drafts",
        "telegram_bot_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
        postgresql_using="telegram_bot_id::bigint",
    )


def downgrade() -> None:
    op.alter_column(
        "project_setup_drafts",
        "telegram_bot_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
        postgresql_using="telegram_bot_id::integer",
    )
