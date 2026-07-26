"""VIP reveal checkout context.

Revision ID: 20260726_0003
Revises: 20260726_0002
"""

from alembic import op
import sqlalchemy as sa

revision = "20260726_0003"
down_revision = "20260726_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reveal_checkouts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("buyer_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("customer_operation_id", sa.String(64)),
        sa.Column("invoice_id", sa.String(64)),
        sa.Column("transaction_id", sa.String(64)),
        sa.Column(
            "status",
            sa.String(24),
            nullable=False,
            server_default="created",
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
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
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["buyer_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "question_id",
            "buyer_id",
            name="uq_reveal_checkout_question_buyer",
        ),
        sa.UniqueConstraint("token"),
        sa.UniqueConstraint("customer_operation_id"),
        sa.UniqueConstraint("invoice_id"),
        sa.UniqueConstraint("transaction_id"),
    )
    op.create_index(
        "ix_reveal_checkouts_question_id",
        "reveal_checkouts",
        ["question_id"],
    )
    op.create_index(
        "ix_reveal_checkouts_buyer_id",
        "reveal_checkouts",
        ["buyer_id"],
    )
    op.create_index(
        "ix_reveal_checkouts_token",
        "reveal_checkouts",
        ["token"],
    )
    op.create_index(
        "ix_reveal_checkouts_customer_operation_id",
        "reveal_checkouts",
        ["customer_operation_id"],
    )
    op.create_index(
        "ix_reveal_checkouts_status",
        "reveal_checkouts",
        ["status"],
    )


def downgrade() -> None:
    op.drop_table("reveal_checkouts")
