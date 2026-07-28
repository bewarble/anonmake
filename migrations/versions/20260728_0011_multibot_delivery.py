"""multibot delivery and broadcasts

Revision ID: 20260728_0011
Revises: 20260728_0010
"""

from alembic import op
import sqlalchemy as sa


revision = "20260728_0011"
down_revision = "20260728_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "delivery_outbox",
        sa.Column("bot_id", sa.Integer(), nullable=True),
    )
    op.execute("UPDATE delivery_outbox SET bot_id = 1 WHERE bot_id IS NULL")
    op.alter_column("delivery_outbox", "bot_id", nullable=False)
    op.create_foreign_key(
        "fk_delivery_outbox_bot_id_bot_instances",
        "delivery_outbox",
        "bot_instances",
        ["bot_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_delivery_outbox_bot_id",
        "delivery_outbox",
        ["bot_id"],
        unique=False,
    )
    op.drop_constraint(
        "uq_delivery_outbox_dedupe_key",
        "delivery_outbox",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_delivery_outbox_bot_dedupe",
        "delivery_outbox",
        ["bot_id", "dedupe_key"],
    )

    op.add_column(
        "broadcasts",
        sa.Column("bot_id", sa.Integer(), nullable=True),
    )
    op.execute("UPDATE broadcasts SET bot_id = 1 WHERE bot_id IS NULL")
    op.alter_column("broadcasts", "bot_id", nullable=False)
    op.create_foreign_key(
        "fk_broadcasts_bot_id_bot_instances",
        "broadcasts",
        "bot_instances",
        ["bot_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_broadcasts_bot_id",
        "broadcasts",
        ["bot_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_broadcasts_bot_id", table_name="broadcasts")
    op.drop_constraint(
        "fk_broadcasts_bot_id_bot_instances",
        "broadcasts",
        type_="foreignkey",
    )
    op.drop_column("broadcasts", "bot_id")

    op.drop_constraint(
        "uq_delivery_outbox_bot_dedupe",
        "delivery_outbox",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_delivery_outbox_dedupe_key",
        "delivery_outbox",
        ["dedupe_key"],
    )
    op.drop_index("ix_delivery_outbox_bot_id", table_name="delivery_outbox")
    op.drop_constraint(
        "fk_delivery_outbox_bot_id_bot_instances",
        "delivery_outbox",
        type_="foreignkey",
    )
    op.drop_column("delivery_outbox", "bot_id")
