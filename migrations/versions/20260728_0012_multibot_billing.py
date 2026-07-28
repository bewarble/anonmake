"""multibot billing and source isolation

Revision ID: 20260728_0012
Revises: 20260728_0011
"""

from alembic import op
import sqlalchemy as sa


revision = "20260728_0012"
down_revision = "20260728_0011"
branch_labels = None
depends_on = None


def _drop_unique(table_name: str, columns: tuple[str, ...]) -> None:
    """Drop an existing unique constraint or unique index by its columns."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    expected = set(columns)

    for constraint in inspector.get_unique_constraints(table_name):
        actual = set(constraint.get("column_names") or ())
        name = constraint.get("name")

        if name and actual == expected:
            op.drop_constraint(
                name,
                table_name,
                type_="unique",
            )
            return

    for index in inspector.get_indexes(table_name):
        actual = set(index.get("column_names") or ())
        name = index.get("name")

        if name and index.get("unique") and actual == expected:
            op.drop_index(
                name,
                table_name=table_name,
            )
            return

    raise RuntimeError(
        f"Unique object not found: {table_name}({', '.join(columns)})"
    )


def _add_bot_id(table: str) -> None:
    op.add_column(table, sa.Column("bot_id", sa.Integer(), nullable=True))
    op.execute(
        f"""
        UPDATE {table} AS target
        SET bot_id = users.bot_id
        FROM users
        WHERE target.user_id = users.id
          AND target.bot_id IS NULL
        """
    )
    op.alter_column(table, "bot_id", nullable=False)
    op.create_foreign_key(
        f"fk_{table}_bot_id_bot_instances",
        table,
        "bot_instances",
        ["bot_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(f"ix_{table}_bot_id", table, ["bot_id"], unique=False)


def upgrade() -> None:
    _add_bot_id("payment_methods")
    _add_bot_id("subscriptions")

    op.add_column("payment_attempts", sa.Column("bot_id", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE payment_attempts AS attempts
        SET bot_id = subscriptions.bot_id
        FROM subscriptions
        WHERE attempts.subscription_id = subscriptions.id
          AND attempts.bot_id IS NULL
        """
    )
    op.alter_column("payment_attempts", "bot_id", nullable=False)
    op.create_foreign_key(
        "fk_payment_attempts_bot_id_bot_instances",
        "payment_attempts",
        "bot_instances",
        ["bot_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_payment_attempts_bot_id", "payment_attempts", ["bot_id"])

    op.add_column("traffic_sources", sa.Column("bot_id", sa.Integer(), nullable=True))
    op.execute("UPDATE traffic_sources SET bot_id = 1 WHERE bot_id IS NULL")
    op.alter_column("traffic_sources", "bot_id", nullable=False)
    op.create_foreign_key(
        "fk_traffic_sources_bot_id_bot_instances",
        "traffic_sources",
        "bot_instances",
        ["bot_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_traffic_sources_bot_id", "traffic_sources", ["bot_id"])

    _drop_unique("payment_methods", ("user_id",))
    _drop_unique("payment_methods", ("merchant_user_id",))
    _drop_unique("payment_methods", ("impaya_operation_id",))
    _drop_unique("payment_methods", ("binding_id",))
    _drop_unique("subscriptions", ("user_id",))
    _drop_unique("payment_attempts", ("customer_operation_id",))
    _drop_unique(
        "payment_attempts",
        ("subscription_id", "billing_cycle_key", "attempt_kind"),
    )
    _drop_unique("traffic_sources", ("code",))

    op.create_unique_constraint("uq_payment_methods_bot_user", "payment_methods", ["bot_id", "user_id"])
    op.create_unique_constraint(
        "uq_payment_methods_bot_merchant_user",
        "payment_methods",
        ["bot_id", "merchant_user_id"],
    )
    op.create_unique_constraint(
        "uq_payment_methods_bot_impaya_operation",
        "payment_methods",
        ["bot_id", "impaya_operation_id"],
    )
    op.create_unique_constraint(
        "uq_payment_methods_bot_binding",
        "payment_methods",
        ["bot_id", "binding_id"],
    )
    op.create_unique_constraint("uq_subscriptions_bot_user", "subscriptions", ["bot_id", "user_id"])
    op.create_unique_constraint(
        "uq_payment_attempt_bot_operation",
        "payment_attempts",
        ["bot_id", "customer_operation_id"],
    )
    op.create_unique_constraint(
        "uq_payment_attempt_bot_cycle_kind",
        "payment_attempts",
        ["bot_id", "subscription_id", "billing_cycle_key", "attempt_kind"],
    )
    op.create_unique_constraint(
        "uq_traffic_sources_bot_code",
        "traffic_sources",
        ["bot_id", "code"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_traffic_sources_bot_code", "traffic_sources", type_="unique")
    op.drop_constraint("uq_payment_attempt_bot_cycle_kind", "payment_attempts", type_="unique")
    op.drop_constraint("uq_payment_attempt_bot_operation", "payment_attempts", type_="unique")
    op.drop_constraint("uq_subscriptions_bot_user", "subscriptions", type_="unique")
    op.drop_constraint("uq_payment_methods_bot_binding", "payment_methods", type_="unique")
    op.drop_constraint("uq_payment_methods_bot_impaya_operation", "payment_methods", type_="unique")
    op.drop_constraint("uq_payment_methods_bot_merchant_user", "payment_methods", type_="unique")
    op.drop_constraint("uq_payment_methods_bot_user", "payment_methods", type_="unique")

    op.create_unique_constraint("uq_traffic_sources_code", "traffic_sources", ["code"])
    op.create_unique_constraint(
        "uq_payment_attempt_cycle_kind",
        "payment_attempts",
        ["subscription_id", "billing_cycle_key", "attempt_kind"],
    )
    op.create_unique_constraint(
        "payment_attempts_customer_operation_id_key",
        "payment_attempts",
        ["customer_operation_id"],
    )
    op.create_unique_constraint("subscriptions_user_id_key", "subscriptions", ["user_id"])
    op.create_unique_constraint("payment_methods_binding_id_key", "payment_methods", ["binding_id"])
    op.create_unique_constraint(
        "payment_methods_impaya_operation_id_key",
        "payment_methods",
        ["impaya_operation_id"],
    )
    op.create_unique_constraint(
        "payment_methods_merchant_user_id_key",
        "payment_methods",
        ["merchant_user_id"],
    )
    op.create_unique_constraint("payment_methods_user_id_key", "payment_methods", ["user_id"])

    for table in ("traffic_sources", "payment_attempts", "subscriptions", "payment_methods"):
        op.drop_index(f"ix_{table}_bot_id", table_name=table)
        op.drop_constraint(
            f"fk_{table}_bot_id_bot_instances",
            table,
            type_="foreignkey",
        )
        op.drop_column(table, "bot_id")
