"""project profiles and setup wizard drafts

Revision ID: 20260728_0018
Revises: 20260728_0017
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260728_0018"
down_revision = "20260728_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bot_instances", sa.Column("description", sa.Text()))
    op.add_column("bot_instances", sa.Column("profile_code", sa.String(48)))
    op.add_column("bot_instances", sa.Column("setup_status", sa.String(32), nullable=False, server_default="running"))
    op.create_index("ix_bot_instances_profile_code", "bot_instances", ["profile_code"])
    op.create_index("ix_bot_instances_setup_status", "bot_instances", ["setup_status"])

    op.create_table("project_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(48), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("defaults", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_project_profiles_code", "project_profiles", ["code"], unique=True)
    op.execute("""INSERT INTO project_profiles (code, name, description, defaults) VALUES ('anonymous_questions', 'Анонимные вопросы', 'Стандартный профиль AnonMake для анонимных вопросов и VIP-доступа.', '{}'::jsonb)""")

    op.create_table("project_setup_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_by_admin_id", sa.Integer(), sa.ForeignKey("admin_users.id", ondelete="SET NULL")),
        sa.Column("profile_code", sa.String(48), nullable=False, server_default="anonymous_questions"),
        sa.Column("code", sa.String(32)), sa.Column("display_name", sa.String(96)), sa.Column("description", sa.Text()),
        sa.Column("telegram_username", sa.String(64)), sa.Column("telegram_bot_id", sa.BigInteger()),
        sa.Column("telegram_token_encrypted", sa.Text()), sa.Column("telegram_token_hint", sa.String(32)), sa.Column("telegram_verified_at", sa.DateTime(timezone=True)),
        sa.Column("impaya_api_url", sa.String(512)), sa.Column("impaya_api_token_encrypted", sa.Text()),
        sa.Column("impaya_terminal_name", sa.String(128)), sa.Column("impaya_binding_terminal_name", sa.String(128)), sa.Column("impaya_recurrent_terminal_name", sa.String(128)),
        sa.Column("impaya_payment_form_url_template", sa.String(1024)), sa.Column("impaya_webhook_secret_encrypted", sa.Text()),
        sa.Column("assigned_admin_id", sa.Integer(), sa.ForeignKey("admin_users.id", ondelete="SET NULL")),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("validation_errors", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("launched_bot_id", sa.Integer(), sa.ForeignKey("bot_instances.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_project_setup_drafts_created_by_admin_id", "project_setup_drafts", ["created_by_admin_id"])
    op.create_index("ix_project_setup_drafts_assigned_admin_id", "project_setup_drafts", ["assigned_admin_id"])
    op.create_index("ix_project_setup_drafts_code", "project_setup_drafts", ["code"])
    op.create_index("ix_project_setup_drafts_status", "project_setup_drafts", ["status"])


def downgrade() -> None:
    op.drop_table("project_setup_drafts")
    op.drop_table("project_profiles")
    op.drop_index("ix_bot_instances_setup_status", table_name="bot_instances")
    op.drop_index("ix_bot_instances_profile_code", table_name="bot_instances")
    op.drop_column("bot_instances", "setup_status")
    op.drop_column("bot_instances", "profile_code")
    op.drop_column("bot_instances", "description")
