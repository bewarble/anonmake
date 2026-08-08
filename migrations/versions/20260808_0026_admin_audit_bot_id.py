from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260808_0026"
down_revision = "20260808_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "admin_audit_logs",
        sa.Column("bot_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_admin_audit_logs_bot_id_bot_instances",
        "admin_audit_logs",
        "bot_instances",
        ["bot_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_admin_audit_logs_bot_id",
        "admin_audit_logs",
        ["bot_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_admin_audit_logs_bot_id", table_name="admin_audit_logs")
    op.drop_constraint(
        "fk_admin_audit_logs_bot_id_bot_instances",
        "admin_audit_logs",
        type_="foreignkey",
    )
    op.drop_column("admin_audit_logs", "bot_id")
