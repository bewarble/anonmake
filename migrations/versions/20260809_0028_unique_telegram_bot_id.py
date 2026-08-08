from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260809_0028"
down_revision = "20260808_0027"
branch_labels = None
depends_on = None


INDEX_NAME = "ix_bot_instances_telegram_bot_id"


def upgrade() -> None:
    connection = op.get_bind()
    duplicates = connection.execute(
        sa.text(
            """
            SELECT telegram_bot_id
            FROM bot_instances
            WHERE telegram_bot_id IS NOT NULL
            GROUP BY telegram_bot_id
            HAVING COUNT(*) > 1
            ORDER BY telegram_bot_id
            """
        )
    ).scalars().all()
    if duplicates:
        rendered = ", ".join(str(value) for value in duplicates[:20])
        raise RuntimeError(
            "Duplicate Telegram bot ownership must be resolved before migration: "
            + rendered
        )

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
