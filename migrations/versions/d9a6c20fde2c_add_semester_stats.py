"""Keep each semester's counts, for pages that show many classes at once.

Rows are filled on demand, so none are added here. Row-level security is on, as for
every table on Postgres.

Revision ID: d9a6c20fde2c
Revises: 32c2195ca095
Create Date: 2026-09-25 00:10:00

"""

import sqlalchemy as sa
from alembic import op

revision = "d9a6c20fde2c"
down_revision = "32c2195ca095"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "semester_stats",
        sa.Column("semester_id", sa.Integer(), nullable=False),
        sa.Column("students", sa.Integer(), nullable=False),
        sa.Column("at_risk", sa.Integer(), nullable=False),
        sa.Column("pending", sa.Integer(), nullable=False),
        sa.Column("computed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["semester_id"],
            ["semesters.id"],
            name=op.f("fk_semester_stats_semester_id_semesters"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("semester_id", name=op.f("pk_semester_stats")),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute('ALTER TABLE "semester_stats" ENABLE ROW LEVEL SECURITY')


def downgrade():
    op.drop_table("semester_stats")
