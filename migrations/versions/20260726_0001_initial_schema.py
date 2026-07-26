"""Initial users, questions and answers schema.

Revision ID: 20260726_0001
Revises:
Create Date: 2026-07-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260726_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("public_code", sa.String(length=32), nullable=False),
        sa.Column("username", sa.String(length=32), nullable=True),
        sa.Column("first_name", sa.String(length=64), nullable=False),
        sa.Column("last_name", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("public_code", name="uq_users_public_code"),
        sa.UniqueConstraint("telegram_id", name="uq_users_telegram_id"),
    )
    op.create_index("ix_users_public_code", "users", ["public_code"], unique=True)
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("recipient_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], name="fk_questions_recipient_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], name="fk_questions_sender_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_questions"),
    )
    op.create_index("ix_questions_recipient_id", "questions", ["recipient_id"], unique=False)
    op.create_index("ix_questions_sender_id", "questions", ["sender_id"], unique=False)
    op.create_index("ix_questions_status", "questions", ["status"], unique=False)

    op.create_table(
        "answers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], name="fk_answers_question_id_questions", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_answers"),
        sa.UniqueConstraint("question_id", name="uq_answers_question_id"),
    )
    op.create_index("ix_answers_question_id", "answers", ["question_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_answers_question_id", table_name="answers")
    op.drop_table("answers")
    op.drop_index("ix_questions_status", table_name="questions")
    op.drop_index("ix_questions_sender_id", table_name="questions")
    op.drop_index("ix_questions_recipient_id", table_name="questions")
    op.drop_table("questions")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_index("ix_users_public_code", table_name="users")
    op.drop_table("users")
