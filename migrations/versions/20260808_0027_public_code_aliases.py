from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = "20260808_0027"
down_revision = "20260808_0026"
branch_labels = None
depends_on = None

SNAPSHOT_TABLE = "public_code_rotation_snapshot"


def _snapshot_exists() -> bool:
    bind = op.get_bind()
    return bool(
        bind.execute(
            text("SELECT to_regclass(:table_name) IS NOT NULL"),
            {"table_name": SNAPSHOT_TABLE},
        ).scalar()
    )


def _import_snapshot() -> None:
    if not _snapshot_exists():
        return

    bind = op.get_bind()
    conflict = bind.execute(
        text(
            f"""
            SELECT s.bot_id, s.user_id, s.public_code, u.id AS current_user_id
              FROM {SNAPSHOT_TABLE} s
              JOIN users u
                ON u.bot_id = s.bot_id
               AND u.public_code = s.public_code
               AND u.id <> s.user_id
             LIMIT 1
            """
        )
    ).mappings().first()
    if conflict is not None:
        raise RuntimeError(
            "Historical public-code alias conflicts with another current user: "
            f"bot_id={conflict['bot_id']} code={conflict['public_code']} "
            f"historical_user_id={conflict['user_id']} "
            f"current_user_id={conflict['current_user_id']}"
        )

    bind.execute(
        text(
            f"""
            INSERT INTO user_public_code_aliases (bot_id, user_id, public_code)
            SELECT s.bot_id, s.user_id, s.public_code
              FROM {SNAPSHOT_TABLE} s
              JOIN users u
                ON u.id = s.user_id
               AND u.bot_id = s.bot_id
             WHERE s.public_code <> u.public_code
            ON CONFLICT (bot_id, public_code) DO NOTHING
            """
        )
    )
    bind.execute(text(f"DROP TABLE {SNAPSHOT_TABLE}"))


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
    _import_snapshot()


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        text(
            f"""
            CREATE TABLE IF NOT EXISTS {SNAPSHOT_TABLE} (
                bot_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                public_code VARCHAR(32) NOT NULL,
                stage VARCHAR(16) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (bot_id, public_code)
            )
            """
        )
    )
    bind.execute(
        text(
            f"""
            INSERT INTO {SNAPSHOT_TABLE} (bot_id, user_id, public_code, stage)
            SELECT bot_id, user_id, public_code, 'downgrade_0027'
              FROM user_public_code_aliases
            ON CONFLICT (bot_id, public_code) DO NOTHING
            """
        )
    )
    op.drop_index(
        "ix_user_public_code_aliases_user_id",
        table_name="user_public_code_aliases",
    )
    op.drop_table("user_public_code_aliases")
