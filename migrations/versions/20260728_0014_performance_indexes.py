"""performance indexes for multibot workloads

Revision ID: 20260728_0014
Revises: 20260728_0013
"""

from alembic import op

revision = "20260728_0014"
down_revision = "20260728_0013"
branch_labels = None
depends_on = None

INDEXES = (
    ("ix_delivery_claim", "delivery_outbox", ["status", "next_attempt_at", "locked_at", "id"]),
    ("ix_delivery_bot_status_created", "delivery_outbox", ["bot_id", "status", "created_at"]),
    ("ix_broadcast_status_id", "broadcasts", ["status", "id"]),
    ("ix_broadcast_bot_status", "broadcasts", ["bot_id", "status"]),
    ("ix_subscription_due", "subscriptions", ["auto_renew", "next_charge_at", "id"]),
    ("ix_subscription_bot_status", "subscriptions", ["bot_id", "status"]),
    ("ix_payment_attempt_bot_status_created", "payment_attempts", ["bot_id", "status", "created_at"]),
    ("ix_users_bot_created", "users", ["bot_id", "created_at"]),
)


def upgrade() -> None:
    for name, table, columns in INDEXES:
        op.create_index(name, table, columns, unique=False, if_not_exists=True)


def downgrade() -> None:
    for name, table, _columns in reversed(INDEXES):
        op.drop_index(name, table_name=table, if_exists=True)
