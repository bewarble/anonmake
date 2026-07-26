"""Automatic payment notification state.

Revision ID: 20260726_0004
Revises: 20260726_0003
"""

from alembic import op
import sqlalchemy as sa

revision = "20260726_0004"
down_revision = "20260726_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "reveal_checkouts",
        sa.Column("notified_at", sa.DateTime(timezone=True)),
    )
    op.add_column(
        "reveal_checkouts",
        sa.Column("notification_error", sa.String(512)),
    )


def downgrade() -> None:
    op.drop_column("reveal_checkouts", "notification_error")
    op.drop_column("reveal_checkouts", "notified_at")
