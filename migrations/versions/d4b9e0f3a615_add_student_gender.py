"""Keep whether a student is a son or a daughter, for the message's wording.

Revision ID: d4b9e0f3a615
Revises: c6f2a8e41d73
Create Date: 2026-09-25 15:00:00

"""

import sqlalchemy as sa
from alembic import op

revision = "d4b9e0f3a615"
down_revision = "c6f2a8e41d73"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("students", schema=None) as batch_op:
        batch_op.add_column(sa.Column("gender", sa.String(length=6), nullable=True))
        batch_op.create_check_constraint("gender", "gender IN ('male', 'female')")


def downgrade():
    with op.batch_alter_table("students", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_students_gender"), type_="check")
        batch_op.drop_column("gender")
