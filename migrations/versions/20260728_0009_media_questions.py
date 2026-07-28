"""media questions and delivery payload

Revision ID: 20260728_0009
Revises: 20260726_0008
Create Date: 2026-07-28
"""

from alembic import op
import sqlalchemy as sa

revision = "20260728_0009"
down_revision = "20260726_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "questions",
        sa.Column(
            "content_type",
            sa.String(length=24),
            nullable=False,
            server_default="text",
        ),
    )
    op.add_column(
        "questions",
        sa.Column("media_file_id", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "questions",
        sa.Column("media_caption", sa.Text(), nullable=True),
    )
    op.add_column(
        "delivery_outbox",
        sa.Column("payload", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("delivery_outbox", "payload")
    op.drop_column("questions", "media_caption")
    op.drop_column("questions", "media_file_id")
    op.drop_column("questions", "content_type")
