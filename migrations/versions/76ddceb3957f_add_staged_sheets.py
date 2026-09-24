"""Keep staged sheets in the database, between the review page and Confirm.

Revision ID: 76ddceb3957f
Revises: 059d9c237bd1
Create Date: 2026-09-24 11:58:19

"""

import sqlalchemy as sa
from alembic import op

revision = "76ddceb3957f"
down_revision = "059d9c237bd1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "staged_sheets",
        sa.Column("token", sa.String(length=32), nullable=False),
        sa.Column("mentor_id", sa.Integer(), nullable=False),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("semester_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=120), nullable=False),
        sa.Column("sheet", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["class_id"],
            ["classes.id"],
            name=op.f("fk_staged_sheets_class_id_classes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["mentor_id"],
            ["mentors.id"],
            name=op.f("fk_staged_sheets_mentor_id_mentors"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["semester_id"],
            ["semesters.id"],
            name=op.f("fk_staged_sheets_semester_id_semesters"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("token", name=op.f("pk_staged_sheets")),
    )
    with op.batch_alter_table("staged_sheets", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_staged_sheets_created_at"), ["created_at"], unique=False
        )


def downgrade():
    with op.batch_alter_table("staged_sheets", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_staged_sheets_created_at"))

    op.drop_table("staged_sheets")
