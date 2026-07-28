"""platform administrator accounts and per-project payment gateways

Revision ID: 20260728_0015
Revises: 20260728_0014
"""

from alembic import op
import sqlalchemy as sa


revision = "20260728_0015"
down_revision = "20260728_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_admin_users_email", "admin_users", ["email"], unique=True)
    op.create_index("ix_admin_users_role", "admin_users", ["role"])

    op.create_table(
        "admin_project_access",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("admin_user_id", sa.Integer(), sa.ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("bot_instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("admin_user_id", "bot_id", name="uq_admin_project_access"),
    )
    op.create_index("ix_admin_project_access_admin_user_id", "admin_project_access", ["admin_user_id"])
    op.create_index("ix_admin_project_access_bot_id", "admin_project_access", ["bot_id"])

    op.create_table(
        "payment_gateway_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bot_id", sa.Integer(), sa.ForeignKey("bot_instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False, server_default="impaya"),
        sa.Column("api_url", sa.String(512), nullable=False),
        sa.Column("api_token_encrypted", sa.Text(), nullable=False),
        sa.Column("auth_header", sa.String(64), nullable=False, server_default="Authorization"),
        sa.Column("auth_prefix", sa.String(64), nullable=False, server_default="Bearer "),
        sa.Column("protocol_version", sa.String(32), nullable=False, server_default="v2.0"),
        sa.Column("terminal_name", sa.String(128), nullable=False),
        sa.Column("binding_terminal_name", sa.String(128), nullable=False),
        sa.Column("recurrent_terminal_name", sa.String(128), nullable=False),
        sa.Column("payment_form_url_template", sa.String(1024), nullable=False),
        sa.Column("webhook_secret_encrypted", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("bot_id", "provider", name="uq_gateway_bot_provider"),
    )
    op.create_index("ix_payment_gateway_configs_bot_id", "payment_gateway_configs", ["bot_id"])
    op.create_index("ix_payment_gateway_configs_provider", "payment_gateway_configs", ["provider"])


def downgrade() -> None:
    op.drop_table("payment_gateway_configs")
    op.drop_table("admin_project_access")
    op.drop_table("admin_users")
