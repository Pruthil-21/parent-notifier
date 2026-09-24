"""Add department, role, approval, one-time password and last sign-in to accounts.

Existing accounts stay approved mentors, with no department until they pick one.

Revision ID: 03b02a38ffce
Revises: a41c9e7d2b10
Create Date: 2026-09-24 22:16:37

"""

import sqlalchemy as sa
from alembic import op

revision = "03b02a38ffce"
down_revision = "a41c9e7d2b10"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("mentors", schema=None) as batch_op:
        batch_op.add_column(sa.Column("department", sa.String(length=60), nullable=True))
        batch_op.add_column(
            sa.Column("role", sa.String(length=10), server_default="mentor", nullable=False)
        )
        batch_op.add_column(
            sa.Column("approved", sa.Boolean(), server_default=sa.true(), nullable=False)
        )
        batch_op.add_column(
            sa.Column(
                "must_change_password", sa.Boolean(), server_default=sa.false(), nullable=False
            )
        )
        batch_op.add_column(sa.Column("last_sign_in_at", sa.DateTime(), nullable=True))
        batch_op.create_check_constraint("role", "role IN ('mentor', 'admin')")


def downgrade():
    with op.batch_alter_table("mentors", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_mentors_role"), type_="check")
        batch_op.drop_column("last_sign_in_at")
        batch_op.drop_column("must_change_password")
        batch_op.drop_column("approved")
        batch_op.drop_column("role")
        batch_op.drop_column("department")
