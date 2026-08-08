from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260808_0027"
down_revision = "20260808_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_public_code_aliases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "bot_id",
            sa.Integer(),
            sa.ForeignKey("bot_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("public_code", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "bot_id",
            "public_code",
            name="uq_user_public_code_alias_bot_code",
        ),
    )
    op.create_index(
        "ix_user_public_code_aliases_user_id",
        "user_public_code_aliases",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_public_code_aliases_user_id",
        table_name="user_public_code_aliases",
    )
    op.drop_table("user_public_code_aliases")
