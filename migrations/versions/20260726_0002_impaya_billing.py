"""Impaya recurring billing tables.

Revision ID: 20260726_0002
Revises: 20260726_0001
"""

from alembic import op
import sqlalchemy as sa

revision = "20260726_0002"
down_revision = "20260726_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_methods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("merchant_user_id", sa.String(36), nullable=False),
        sa.Column("impaya_operation_id", sa.String(64)),
        sa.Column("impaya_user_id", sa.String(64)),
        sa.Column("binding_id", sa.String(128)),
        sa.Column("masked_pan", sa.String(32)),
        sa.Column("card_brand", sa.String(32)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_recurrent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("blocked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("merchant_user_id"),
        sa.UniqueConstraint("impaya_operation_id"),
        sa.UniqueConstraint("binding_id"),
    )
    op.create_index("ix_payment_methods_user_id", "payment_methods", ["user_id"])

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("auto_renew", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("access_until", sa.DateTime(timezone=True)),
        sa.Column("next_charge_at", sa.DateTime(timezone=True)),
        sa.Column("last_successful_plan", sa.String(24)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"])
    op.create_index("ix_subscriptions_next_charge_at", "subscriptions", ["next_charge_at"])

    op.create_table(
        "payment_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("customer_operation_id", sa.String(64), nullable=False),
        sa.Column("transaction_id", sa.String(64)),
        sa.Column("billing_cycle_key", sa.String(32), nullable=False),
        sa.Column("attempt_kind", sa.String(16), nullable=False),
        sa.Column("amount_kopecks", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("error_code", sa.String(128)),
        sa.Column("error_message", sa.Text()),
        sa.Column("raw_response", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["subscription_id"], ["subscriptions.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("customer_operation_id"),
        sa.UniqueConstraint("transaction_id"),
        sa.UniqueConstraint(
            "subscription_id", "billing_cycle_key", "attempt_kind",
            name="uq_payment_attempt_cycle_kind",
        ),
    )
    op.create_index(
        "ix_payment_attempts_subscription_id",
        "payment_attempts", ["subscription_id"]
    )
    op.create_index(
        "ix_payment_attempts_billing_cycle_key",
        "payment_attempts", ["billing_cycle_key"]
    )
    op.create_index("ix_payment_attempts_status", "payment_attempts", ["status"])


def downgrade() -> None:
    op.drop_table("payment_attempts")
    op.drop_table("subscriptions")
    op.drop_table("payment_methods")
