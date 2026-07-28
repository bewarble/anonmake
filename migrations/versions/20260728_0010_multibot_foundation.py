"""multibot foundation

Revision ID: 20260728_0010
Revises: 20260728_0009
"""

from alembic import op
import sqlalchemy as sa


revision = "20260728_0010"
down_revision = "20260728_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bot_instances",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=96), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("code", name="uq_bot_instances_code"),
        sa.UniqueConstraint("username", name="uq_bot_instances_username"),
    )
    op.create_index("ix_bot_instances_code", "bot_instances", ["code"], unique=True)
    op.create_index(
        "ix_bot_instances_username",
        "bot_instances",
        ["username"],
        unique=True,
    )

    op.execute(
        """
        INSERT INTO bot_instances
            (id, code, username, display_name, is_active)
        VALUES
            (1, 'primary', 'primary_bot', 'AnonMake', true)
        """
    )

    op.add_column("users", sa.Column("bot_id", sa.Integer(), nullable=True))
    op.execute("UPDATE users SET bot_id = 1 WHERE bot_id IS NULL")
    op.alter_column("users", "bot_id", nullable=False)
    op.create_foreign_key(
        "fk_users_bot_id_bot_instances",
        "users",
        "bot_instances",
        ["bot_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_users_bot_id", "users", ["bot_id"], unique=False)

    op.drop_index(
        "ix_users_telegram_id",
        table_name="users",
    )
    op.drop_index(
        "ix_users_public_code",
        table_name="users",
    )
    op.create_unique_constraint(
        "uq_users_bot_telegram",
        "users",
        ["bot_id", "telegram_id"],
    )
    op.create_unique_constraint(
        "uq_users_bot_public_code",
        "users",
        ["bot_id", "public_code"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_users_bot_public_code", "users", type_="unique")
    op.drop_constraint("uq_users_bot_telegram", "users", type_="unique")
    op.create_index(
        "ix_users_public_code",
        "users",
        ["public_code"],
        unique=True,
    )
    op.create_index(
        "ix_users_telegram_id",
        "users",
        ["telegram_id"],
        unique=True,
    )
    op.drop_index("ix_users_bot_id", table_name="users")
    op.drop_constraint(
        "fk_users_bot_id_bot_instances",
        "users",
        type_="foreignkey",
    )
    op.drop_column("users", "bot_id")
    op.drop_index("ix_bot_instances_username", table_name="bot_instances")
    op.drop_index("ix_bot_instances_code", table_name="bot_instances")
    op.drop_table("bot_instances")
