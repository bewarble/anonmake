"""allow multiple answers per anonymous message

Revision ID: 20260807_0020
Revises: 20260729_0019
"""

from alembic import op


revision = "20260807_0020"
down_revision = "20260729_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_answers_question_id", table_name="answers")
    op.drop_constraint("uq_answers_question_id", "answers", type_="unique")
    op.create_index("ix_answers_question_id", "answers", ["question_id"], unique=False)


def downgrade() -> None:
    # PostgreSQL will refuse this downgrade rather than silently discard replies
    # if a question already has more than one answer.
    op.drop_index("ix_answers_question_id", table_name="answers")
    op.create_unique_constraint("uq_answers_question_id", "answers", ["question_id"])
    op.create_index("ix_answers_question_id", "answers", ["question_id"], unique=True)
