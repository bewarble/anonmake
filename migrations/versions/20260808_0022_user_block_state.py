from __future__ import annotations

from alembic import op
import sqlalchemy as sa


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


def downgrade() -> None:
    op.drop_index("ix_users_is_blocked", table_name="users")
    op.drop_column("users", "blocked_at")
    op.drop_column("users", "is_blocked")
