"""fix legacy user uniqueness for multibot

Revision ID: 20260728_0013
Revises: 20260728_0012
"""

from alembic import op
import sqlalchemy as sa


revision = "20260728_0013"
down_revision = "20260728_0012"
branch_labels = None
depends_on = None


def _drop_unique_for_columns(
    table_name: str,
    columns: tuple[str, ...],
    *,
    preserve: set[str],
) -> None:
    inspector = sa.inspect(op.get_bind())
    expected = set(columns)

    for constraint in inspector.get_unique_constraints(table_name):
        name = constraint.get("name")
        actual = set(constraint.get("column_names") or ())

        if name and name not in preserve and actual == expected:
            op.drop_constraint(name, table_name, type_="unique")

    for index in inspector.get_indexes(table_name):
        name = index.get("name")
        actual = set(index.get("column_names") or ())

        if (
            name
            and name not in preserve
            and index.get("unique")
            and actual == expected
        ):
            op.drop_index(name, table_name=table_name)


def upgrade() -> None:
    preserve = {
        "uq_users_bot_telegram",
        "uq_users_bot_public_code",
    }

    _drop_unique_for_columns(
        "users",
        ("telegram_id",),
        preserve=preserve,
    )
    _drop_unique_for_columns(
        "users",
        ("public_code",),
        preserve=preserve,
    )

    inspector = sa.inspect(op.get_bind())
    existing = {
        item.get("name")
        for item in inspector.get_unique_constraints("users")
    }

    if "uq_users_bot_telegram" not in existing:
        op.create_unique_constraint(
            "uq_users_bot_telegram",
            "users",
            ["bot_id", "telegram_id"],
        )

    if "uq_users_bot_public_code" not in existing:
        op.create_unique_constraint(
            "uq_users_bot_public_code",
            "users",
            ["bot_id", "public_code"],
        )


def downgrade() -> None:
    # Нельзя безопасно вернуть глобальную уникальность:
    # один Telegram-пользователь уже может находиться в нескольких ботах.
    pass
