"""Durable Telegram delivery outbox.

Revision ID: 20260726_0006
Revises: 20260726_0005
"""

from alembic import op
import sqlalchemy as sa

revision = "20260726_0006"
down_revision = "20260726_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "delivery_outbox",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("dedupe_key", sa.String(128), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("reply_markup", sa.JSON()),
        sa.Column(
            "status",
            sa.String(24),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("locked_at", sa.DateTime(timezone=True)),
        sa.Column("locked_by", sa.String(96)),
        sa.Column("telegram_message_id", sa.BigInteger()),
        sa.Column("last_error", sa.String(1000)),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "dedupe_key",
            name="uq_delivery_outbox_dedupe_key",
        ),
    )

    for column in (
        "kind",
        "dedupe_key",
        "chat_id",
        "status",
        "next_attempt_at",
        "locked_by",
        "delivered_at",
        "created_at",
    ):
        op.create_index(
            f"ix_delivery_outbox_{column}",
            "delivery_outbox",
            [column],
        )


def downgrade() -> None:
    op.drop_table("delivery_outbox")
