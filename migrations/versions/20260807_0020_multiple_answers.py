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
    op.drop_constraint("answers_question_id_key", "answers", type_="unique")


def downgrade() -> None:
    # Downgrade is intentionally guarded by PostgreSQL: if multiple replies were
    # already created for one question, restoring uniqueness would be lossy.
    op.create_unique_constraint("answers_question_id_key", "answers", ["question_id"])
