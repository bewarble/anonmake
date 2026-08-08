from __future__ import annotations

from alembic import op


revision = "20260809_0028"
down_revision = "20260808_0027"
branch_labels = None
depends_on = None


INDEX_NAME = "ix_bot_instances_telegram_bot_id"


def upgrade() -> None:
    # PostgreSQL and SQLite both allow multiple NULL values in a unique index,
    # while every verified Telegram bot id must belong to exactly one project.
    op.create_index(
        INDEX_NAME,
        "bot_instances",
        ["telegram_bot_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="bot_instances")
