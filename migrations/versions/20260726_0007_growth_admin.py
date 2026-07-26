"""Traffic sources and broadcasts.

Revision ID: 20260726_0007
Revises: 20260726_0006
"""

from alembic import op
import sqlalchemy as sa

revision = "20260726_0007"
down_revision = "20260726_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "traffic_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("source_url", sa.String(1000), nullable=False),
        sa.Column("spend_kopecks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("code", name="uq_traffic_sources_code"),
    )
    op.create_index("ix_traffic_sources_code", "traffic_sources", ["code"])

    op.create_table(
        "source_attributions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("traffic_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_source_attribution_user"),
    )
    op.create_index("ix_source_attributions_source_id", "source_attributions", ["source_id"])
    op.create_index("ix_source_attributions_user_id", "source_attributions", ["user_id"])
    op.create_index("ix_source_attributions_first_seen_at", "source_attributions", ["first_seen_at"])

    op.create_table(
        "broadcasts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("audience", sa.String(24), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="draft"),
        sa.Column("cursor_user_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("queued_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_broadcasts_kind", "broadcasts", ["kind"])
    op.create_index("ix_broadcasts_audience", "broadcasts", ["audience"])
    op.create_index("ix_broadcasts_status", "broadcasts", ["status"])
    op.create_index("ix_broadcasts_created_at", "broadcasts", ["created_at"])


def downgrade() -> None:
    op.drop_table("broadcasts")
    op.drop_table("source_attributions")
    op.drop_table("traffic_sources")
