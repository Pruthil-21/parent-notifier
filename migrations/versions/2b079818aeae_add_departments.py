"""Keep departments in a table, starting with the college's twelve.

Mentors and classes keep storing the department's name. Row-level security is switched
on for the new table, as for every table on Postgres.

Revision ID: 2b079818aeae
Revises: 03b02a38ffce
Create Date: 2026-09-24 22:26:41

"""

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "2b079818aeae"
down_revision = "03b02a38ffce"
branch_labels = None
depends_on = None

DEPARTMENTS = (
    "Applied Science & Humanities",
    "Chemical Engineering",
    "Civil Engineering",
    "Computer Engineering",
    "Computer Science and Design",
    "Computer Science and Engineering (IOT)",
    "Electrical Engineering",
    "Electronics & Communication",
    "Information & Communication Technology",
    "Information Technology",
    "Mechanical Engineering",
    "Mechatronics Engineering",
)


def upgrade():
    table = op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_departments")),
        sa.UniqueConstraint("name", name=op.f("uq_departments_name")),
    )
    now = datetime.now(UTC).replace(tzinfo=None)
    op.bulk_insert(
        table, [{"name": name, "created_at": now, "updated_at": now} for name in DEPARTMENTS]
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute('ALTER TABLE "departments" ENABLE ROW LEVEL SECURITY')


def downgrade():
    op.drop_table("departments")
