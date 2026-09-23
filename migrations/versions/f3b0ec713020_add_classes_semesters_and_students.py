"""Add classes, semesters and students.

Revision ID: f3b0ec713020
Revises: 7857aa5be352
Create Date: 2026-09-23 23:16:20

"""

import sqlalchemy as sa
from alembic import op

revision = "f3b0ec713020"
down_revision = "7857aa5be352"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "classes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mentor_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("department", sa.String(length=80), nullable=False),
        sa.Column("admission_year", sa.Integer(), nullable=False),
        sa.Column("attendance_threshold", sa.Integer(), server_default="75", nullable=False),
        sa.Column("midsem_pass_mark", sa.Integer(), server_default="7", nullable=False),
        sa.Column("midsem_max", sa.Integer(), server_default="20", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "attendance_threshold BETWEEN 1 AND 100", name=op.f("ck_classes_attendance_threshold")
        ),
        sa.CheckConstraint("midsem_max BETWEEN 1 AND 100", name=op.f("ck_classes_midsem_max")),
        sa.CheckConstraint(
            "midsem_pass_mark BETWEEN 0 AND midsem_max", name=op.f("ck_classes_midsem_pass_mark")
        ),
        sa.ForeignKeyConstraint(
            ["mentor_id"],
            ["mentors.id"],
            name=op.f("fk_classes_mentor_id_mentors"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_classes")),
        sa.UniqueConstraint("mentor_id", "name", name=op.f("uq_classes_mentor_id_name")),
    )
    op.create_table(
        "semesters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("current_round", sa.Integer(), server_default="0", nullable=False),
        sa.Column("round_counter", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_imported_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("number BETWEEN 1 AND 12", name=op.f("ck_semesters_number")),
        sa.ForeignKeyConstraint(
            ["class_id"],
            ["classes.id"],
            name=op.f("fk_semesters_class_id_classes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_semesters")),
        sa.UniqueConstraint("class_id", "number", name=op.f("uq_semesters_class_id_number")),
    )
    op.create_table(
        "students",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("enrollment_no", sa.String(length=30), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("parent_name", sa.String(length=120), server_default="", nullable=False),
        sa.Column("phone_raw", sa.String(length=40), server_default="", nullable=False),
        sa.Column("phone_e164", sa.String(length=16), nullable=True),
        sa.Column("status", sa.String(length=10), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'left', 'detained')", name=op.f("ck_students_status")
        ),
        sa.ForeignKeyConstraint(
            ["class_id"],
            ["classes.id"],
            name=op.f("fk_students_class_id_classes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_students")),
        sa.UniqueConstraint(
            "class_id", "enrollment_no", name=op.f("uq_students_class_id_enrollment_no")
        ),
    )
    op.create_table(
        "semester_students",
        sa.Column("semester_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["semester_id"],
            ["semesters.id"],
            name=op.f("fk_semester_students_semester_id_semesters"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            name=op.f("fk_semester_students_student_id_students"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("semester_id", "student_id", name=op.f("pk_semester_students")),
    )
    with op.batch_alter_table("semester_students", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_semester_students_student_id"), ["student_id"], unique=False
        )


def downgrade():
    with op.batch_alter_table("semester_students", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_semester_students_student_id"))

    op.drop_table("semester_students")
    op.drop_table("students")
    op.drop_table("semesters")
    op.drop_table("classes")
