from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = "20260808_0022"
down_revision = "20260807_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "users",
        sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_is_blocked", "users", ["is_blocked"], unique=False)

    bind = op.get_bind()
    bind.execute(
        text(
            """
            WITH latest_failure AS (
                SELECT
                    u.id AS user_id,
                    MAX(d.updated_at) AS blocked_at
                FROM users u
                JOIN delivery_outbox d
                  ON d.bot_id = u.bot_id
                 AND d.chat_id = u.telegram_id
                WHERE d.status = 'failed'
                  AND (
                    LOWER(COALESCE(d.last_error, '')) LIKE '%bot was blocked%'
                    OR LOWER(COALESCE(d.last_error, '')) LIKE '%chat not found%'
                    OR LOWER(COALESCE(d.last_error, '')) LIKE '%user is deactivated%'
                  )
                GROUP BY u.id
            )
            UPDATE users AS u
               SET is_blocked = TRUE,
                   blocked_at = lf.blocked_at
              FROM latest_failure lf
             WHERE u.id = lf.user_id
               AND lf.blocked_at > u.updated_at
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_users_is_blocked", table_name="users")
    op.drop_column("users", "blocked_at")
    op.drop_column("users", "is_blocked")
