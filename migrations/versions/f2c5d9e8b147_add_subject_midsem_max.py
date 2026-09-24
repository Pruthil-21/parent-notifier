"""Let a subject's Mid-Sem be out of its own total, such as 25.

Revision ID: f2c5d9e8b147
Revises: e8a1c47b2d90
Create Date: 2026-09-25 17:00:00

"""

import sqlalchemy as sa
from alembic import op

revision = "f2c5d9e8b147"
down_revision = "e8a1c47b2d90"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("semester_subjects", schema=None) as batch_op:
        batch_op.add_column(sa.Column("midsem_max", sa.Integer(), nullable=True))
        batch_op.create_check_constraint("midsem_max", "midsem_max BETWEEN 1 AND 100")


def downgrade():
    with op.batch_alter_table("semester_subjects", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_semester_subjects_midsem_max"), type_="check")
        batch_op.drop_column("midsem_max")
