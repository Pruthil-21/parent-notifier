"""Add the send log.

Revision ID: 059d9c237bd1
Revises: c2abc1027afb
Create Date: 2026-09-24 01:17:47

"""

import sqlalchemy as sa
from alembic import op

revision = "059d9c237bd1"
down_revision = "c2abc1027afb"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "send_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("semester_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("mentor_id", sa.Integer(), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("language", sa.String(length=2), nullable=False),
        sa.Column("note", sa.String(length=500), server_default="", nullable=False),
        sa.Column("message", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("language IN ('en', 'gu')", name=op.f("ck_send_log_language")),
        sa.CheckConstraint("status IN ('sent', 'skipped')", name=op.f("ck_send_log_status")),
        sa.ForeignKeyConstraint(
            ["mentor_id"],
            ["mentors.id"],
            name=op.f("fk_send_log_mentor_id_mentors"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["semester_id"],
            ["semesters.id"],
            name=op.f("fk_send_log_semester_id_semesters"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            name=op.f("fk_send_log_student_id_students"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_send_log")),
    )
    with op.batch_alter_table("send_log", schema=None) as batch_op:
        batch_op.create_index(
            "ix_send_log_mentor_created", ["mentor_id", "created_at"], unique=False
        )
        batch_op.create_index("ix_send_log_semester_round", ["semester_id", "round"], unique=False)


def downgrade():
    with op.batch_alter_table("send_log", schema=None) as batch_op:
        batch_op.drop_index("ix_send_log_semester_round")
        batch_op.drop_index("ix_send_log_mentor_created")

    op.drop_table("send_log")
