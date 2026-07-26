"""Growth CRM foundation.

Revision ID: 20260726_0008
Revises: 20260726_0007
"""

from alembic import op
import sqlalchemy as sa

revision = "20260726_0008"
down_revision = "20260726_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crm_tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(48), nullable=False),
        sa.Column("created_by_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("name", name="uq_crm_tags_name"),
    )
    op.create_index("ix_crm_tags_name", "crm_tags", ["name"])

    op.create_table(
        "crm_user_tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("crm_tags.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_by_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "tag_id", name="uq_crm_user_tag"),
    )
    op.create_index("ix_crm_user_tags_user_id", "crm_user_tags", ["user_id"])
    op.create_index("ix_crm_user_tags_tag_id", "crm_user_tags", ["tag_id"])

    op.create_table(
        "crm_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_by_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_crm_notes_user_id", "crm_notes", ["user_id"])
    op.create_index("ix_crm_notes_created_at", "crm_notes", ["created_at"])

    op.create_table(
        "crm_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(48), nullable=False),
        sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("external_key", sa.String(128)),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("external_key", name="uq_crm_events_external_key"),
    )
    op.create_index("ix_crm_events_user_id", "crm_events", ["user_id"])
    op.create_index("ix_crm_events_event_type", "crm_events", ["event_type"])
    op.create_index("ix_crm_events_external_key", "crm_events", ["external_key"])
    op.create_index("ix_crm_events_occurred_at", "crm_events", ["occurred_at"])


def downgrade() -> None:
    op.drop_table("crm_events")
    op.drop_table("crm_notes")
    op.drop_table("crm_user_tags")
    op.drop_table("crm_tags")
