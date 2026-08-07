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


def _code(min_length: int, max_length: int) -> str:
    length = secrets.choice(tuple(range(min_length, max_length + 1)))
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def _regenerate(min_length: int, max_length: int) -> None:
    bind = op.get_bind()
    rows = bind.execute(
        text("SELECT id, bot_id, public_code FROM users ORDER BY bot_id, id")
    ).mappings().all()

    used: dict[int, set[str]] = {}
    for row in rows:
        used.setdefault(int(row["bot_id"]), set()).add(str(row["public_code"]))

    for row in rows:
        bot_id = int(row["bot_id"])
        old_code = str(row["public_code"])
        taken = used[bot_id]
        taken.discard(old_code)

        while True:
            new_code = _code(min_length, max_length)
            if new_code not in taken:
                break

        bind.execute(
            text("UPDATE users SET public_code = :code WHERE id = :user_id"),
            {"code": new_code, "user_id": int(row["id"])},
        )
        taken.add(new_code)


def upgrade() -> None:
    _regenerate(5, 6)


def downgrade() -> None:
    _regenerate(8, 8)
