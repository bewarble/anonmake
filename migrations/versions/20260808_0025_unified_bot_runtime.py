from __future__ import annotations

from alembic import op


revision = "20260808_0025"
down_revision = "20260808_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Stage 64: every Telegram project is owned by app.managed_bots.
    # Legacy projects may still resolve their token from environment variables;
    # projects configured in the admin panel use encrypted DB credentials.
    op.execute("UPDATE bot_instances SET runtime_mode = 'managed'")
    op.alter_column("bot_instances", "runtime_mode", server_default="managed")


def downgrade() -> None:
    op.alter_column("bot_instances", "runtime_mode", server_default="external")
    op.execute("UPDATE bot_instances SET runtime_mode = 'external'")
