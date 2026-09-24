"""Add the announcement banner and who has dismissed it.

Row-level security is on, as for every table on Postgres.

Revision ID: 5e1f0c8b7a24
Revises: a869487a3d2e
Create Date: 2026-09-25 01:10:00

"""

import sqlalchemy as sa
from alembic import op

revision = "5e1f0c8b7a24"
down_revision = "a869487a3d2e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "announcements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(length=300), nullable=False),
        sa.Column("dismissible", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["mentors.id"],
            name=op.f("fk_announcements_created_by_id_mentors"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_announcements")),
    )
    op.create_table(
        "announcement_dismissals",
        sa.Column("announcement_id", sa.Integer(), nullable=False),
        sa.Column("mentor_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["announcement_id"],
            ["announcements.id"],
            name=op.f("fk_announcement_dismissals_announcement_id_announcements"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["mentor_id"],
            ["mentors.id"],
            name=op.f("fk_announcement_dismissals_mentor_id_mentors"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "announcement_id", "mentor_id", name=op.f("pk_announcement_dismissals")
        ),
    )
    if op.get_bind().dialect.name == "postgresql":
        for table in ("announcements", "announcement_dismissals"):
            op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')


def downgrade():
    op.drop_table("announcement_dismissals")
    op.drop_table("announcements")
