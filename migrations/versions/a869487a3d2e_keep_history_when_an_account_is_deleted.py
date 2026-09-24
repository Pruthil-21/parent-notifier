"""Keep message and import history when the account that made it is deleted.

Before, deleting an account also deleted its send log and import records, even for
classes already moved to another mentor. Now the account link is cleared instead.

Revision ID: a869487a3d2e
Revises: d9a6c20fde2c
Create Date: 2026-09-24 23:29:22

"""

import sqlalchemy as sa
from alembic import op

revision = "a869487a3d2e"
down_revision = "d9a6c20fde2c"
branch_labels = None
depends_on = None

TABLES = ("import_batches", "send_log")


def _mentor_link(table: str, ondelete: str, nullable: bool) -> None:
    name = op.f(f"fk_{table}_mentor_id_mentors")
    with op.batch_alter_table(table, schema=None) as batch_op:
        batch_op.alter_column("mentor_id", existing_type=sa.INTEGER(), nullable=nullable)
        batch_op.drop_constraint(name, type_="foreignkey")
        batch_op.create_foreign_key(name, "mentors", ["mentor_id"], ["id"], ondelete=ondelete)


def upgrade():
    for table in TABLES:
        _mentor_link(table, "SET NULL", nullable=True)


def downgrade():
    for table in TABLES:
        _mentor_link(table, "CASCADE", nullable=False)
