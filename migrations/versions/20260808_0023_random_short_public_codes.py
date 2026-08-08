from __future__ import annotations

import secrets
import string

from alembic import op
from sqlalchemy import text


revision = "20260808_0023"
down_revision = "20260808_0022"
branch_labels = None
depends_on = None

ALPHABET = string.ascii_letters + string.digits
SNAPSHOT_TABLE = "public_code_rotation_snapshot"


def _code(min_length: int, max_length: int) -> str:
    length = secrets.choice(tuple(range(min_length, max_length + 1)))
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def _ensure_snapshot_table() -> None:
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


def _snapshot_current_codes(stage: str) -> None:
    bind = op.get_bind()
    _ensure_snapshot_table()
    bind.execute(
        text(
            f"""
            INSERT INTO {SNAPSHOT_TABLE} (bot_id, user_id, public_code, stage)
            SELECT bot_id, id, public_code, :stage
              FROM users
            ON CONFLICT (bot_id, public_code) DO NOTHING
            """
        ),
        {"stage": stage},
    )


def _reserved_codes() -> dict[int, set[str]]:
    bind = op.get_bind()
    _ensure_snapshot_table()
    rows = bind.execute(
        text(f"SELECT bot_id, public_code FROM {SNAPSHOT_TABLE}")
    ).mappings().all()
    reserved: dict[int, set[str]] = {}
    for row in rows:
        reserved.setdefault(int(row["bot_id"]), set()).add(str(row["public_code"]))
    return reserved


def _regenerate(min_length: int, max_length: int) -> None:
    bind = op.get_bind()
    rows = bind.execute(
        text("SELECT id, bot_id, public_code FROM users ORDER BY bot_id, id")
    ).mappings().all()

    active: dict[int, set[str]] = {}
    for row in rows:
        active.setdefault(int(row["bot_id"]), set()).add(str(row["public_code"]))
    reserved = _reserved_codes()

    for row in rows:
        bot_id = int(row["bot_id"])
        old_code = str(row["public_code"])
        taken = active[bot_id]
        taken.discard(old_code)
        historical = reserved.get(bot_id, set())

        while True:
            new_code = _code(min_length, max_length)
            if new_code not in taken and new_code not in historical:
                break

        bind.execute(
            text("UPDATE users SET public_code = :code WHERE id = :user_id"),
            {"code": new_code, "user_id": int(row["id"])},
        )
        taken.add(new_code)


def upgrade() -> None:
    _snapshot_current_codes("before_0023")
    _regenerate(5, 6)


def downgrade() -> None:
    _snapshot_current_codes("downgrade_0023")
    _regenerate(8, 8)
