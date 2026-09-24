"""Switch on row-level security for every table on Postgres.

Hosts such as Supabase can serve tables over a web API. With row-level security on and
no policies, that API returns nothing, while the app keeps full access because it
connects as the owner of the tables. SQLite has no such feature, so it is left as is.

Revision ID: a41c9e7d2b10
Revises: 76ddceb3957f
Create Date: 2026-09-24 13:10:00

"""

from alembic import op

revision = "a41c9e7d2b10"
down_revision = "76ddceb3957f"
branch_labels = None
depends_on = None

TABLES = (
    "alembic_version",
    "classes",
    "import_batches",
    "mentors",
    "results",
    "semester_students",
    "semester_subjects",
    "semesters",
    "send_log",
    "staged_sheets",
    "students",
)


def _set_row_level_security(action: str) -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in TABLES:
        op.execute(f'ALTER TABLE "{table}" {action} ROW LEVEL SECURITY')


def upgrade():
    _set_row_level_security("ENABLE")


def downgrade():
    _set_row_level_security("DISABLE")
