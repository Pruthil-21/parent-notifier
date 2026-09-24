"""Keep the days each semester's attendance covers, for the message.

Revision ID: e8a1c47b2d90
Revises: d4b9e0f3a615
Create Date: 2026-09-25 16:00:00

"""

import sqlalchemy as sa
from alembic import op

revision = "e8a1c47b2d90"
down_revision = "d4b9e0f3a615"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("semesters", schema=None) as batch_op:
        batch_op.add_column(sa.Column("attendance_from", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("attendance_to", sa.Date(), nullable=True))


def downgrade():
    with op.batch_alter_table("semesters", schema=None) as batch_op:
        batch_op.drop_column("attendance_to")
        batch_op.drop_column("attendance_from")
