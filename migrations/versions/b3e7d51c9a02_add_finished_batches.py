"""Let a mentor mark a class's batch as finished.

Revision ID: b3e7d51c9a02
Revises: 5e1f0c8b7a24
Create Date: 2026-09-25 10:00:00

"""

import sqlalchemy as sa
from alembic import op

revision = "b3e7d51c9a02"
down_revision = "5e1f0c8b7a24"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("classes", schema=None) as batch_op:
        batch_op.add_column(sa.Column("finished_at", sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table("classes", schema=None) as batch_op:
        batch_op.drop_column("finished_at")
