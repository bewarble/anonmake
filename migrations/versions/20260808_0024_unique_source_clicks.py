from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260808_0024"
down_revision = "20260808_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_clicks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("traffic_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("source_id", "user_id", name="uq_source_click_source_user"),
    )
    op.create_index("ix_source_clicks_source_id", "source_clicks", ["source_id"])
    op.create_index("ix_source_clicks_user_id", "source_clicks", ["user_id"])
    op.create_index("ix_source_clicks_first_seen_at", "source_clicks", ["first_seen_at"])

    # Existing attribution rows are the only historical visitor identities we can
    # reconstruct safely. Backfill them as one click per source/user pair, then
    # normalize the legacy aggregate counter to the deduplicated data.
    op.execute(
        """
        INSERT INTO source_clicks (source_id, user_id, first_seen_at)
        SELECT source_id, user_id, first_seen_at
        FROM source_attributions
        ON CONFLICT (source_id, user_id) DO NOTHING
        """
    )
    op.execute(
        """
        UPDATE traffic_sources AS source
        SET clicks = (
            SELECT COUNT(*)
            FROM source_clicks AS click
            WHERE click.source_id = source.id
        )
        """
    )


def downgrade() -> None:
    op.drop_index("ix_source_clicks_first_seen_at", table_name="source_clicks")
    op.drop_index("ix_source_clicks_user_id", table_name="source_clicks")
    op.drop_index("ix_source_clicks_source_id", table_name="source_clicks")
    op.drop_table("source_clicks")
