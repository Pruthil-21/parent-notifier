"""Add semester subjects, results and import batches.

Revision ID: c2abc1027afb
Revises: f3b0ec713020
Create Date: 2026-09-24 00:11:08

"""

import sqlalchemy as sa
from alembic import op

revision = "c2abc1027afb"
down_revision = "f3b0ec713020"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "import_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("semester_id", sa.Integer(), nullable=False),
        sa.Column("mentor_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=120), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("previous_round", sa.Integer(), nullable=False),
        sa.Column("added_count", sa.Integer(), nullable=False),
        sa.Column("updated_count", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("undone_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["mentor_id"],
            ["mentors.id"],
            name=op.f("fk_import_batches_mentor_id_mentors"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["semester_id"],
            ["semesters.id"],
            name=op.f("fk_import_batches_semester_id_semesters"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_batches")),
    )
    with op.batch_alter_table("import_batches", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_import_batches_semester_id"), ["semester_id"], unique=False
        )

    op.create_table(
        "semester_subjects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("semester_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["semester_id"],
            ["semesters.id"],
            name=op.f("fk_semester_subjects_semester_id_semesters"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_semester_subjects")),
        sa.UniqueConstraint(
            "semester_id", "name", name=op.f("uq_semester_subjects_semester_id_name")
        ),
    )
    op.create_table(
        "results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("semester_subject_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("theory_pct", sa.Float(), nullable=True),
        sa.Column("practical_pct", sa.Float(), nullable=True),
        sa.Column("midsem_marks", sa.Float(), nullable=True),
        sa.Column("midsem_absent", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.CheckConstraint("midsem_marks >= 0", name=op.f("ck_results_midsem_marks")),
        sa.CheckConstraint(
            "practical_pct BETWEEN 0 AND 100", name=op.f("ck_results_practical_pct")
        ),
        sa.CheckConstraint("theory_pct BETWEEN 0 AND 100", name=op.f("ck_results_theory_pct")),
        sa.ForeignKeyConstraint(
            ["semester_subject_id"],
            ["semester_subjects.id"],
            name=op.f("fk_results_semester_subject_id_semester_subjects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            name=op.f("fk_results_student_id_students"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_results")),
        sa.UniqueConstraint(
            "semester_subject_id",
            "student_id",
            name=op.f("uq_results_semester_subject_id_student_id"),
        ),
    )
    with op.batch_alter_table("results", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_results_student_id"), ["student_id"], unique=False)


def downgrade():
    with op.batch_alter_table("results", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_results_student_id"))

    op.drop_table("results")
    op.drop_table("semester_subjects")
    with op.batch_alter_table("import_batches", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_import_batches_semester_id"))

    op.drop_table("import_batches")
