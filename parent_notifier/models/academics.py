"""Classes (a batch of students under one mentor), their semesters and their students."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    String,
    Table,
    UniqueConstraint,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from parent_notifier.core.extensions import db
from parent_notifier.models.columns import Timestamps, UTCDateTime
from parent_notifier.services.shared import clock

STUDENT_STATUSES = ("active", "left", "detained")
MIN_SEMESTER = 1
MAX_SEMESTER = 12

# Which students appear in which semester's sheet. Students belong to the class; a
# semester only lists who was in it, so detained or lateral-entry students fit naturally.
semester_students = Table(
    "semester_students",
    db.metadata,
    Column("semester_id", ForeignKey("semesters.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "student_id", ForeignKey("students.id", ondelete="CASCADE"), primary_key=True, index=True
    ),
)


class ClassGroup(Timestamps, db.Model):
    """One mentor's class, such as CE-A of the 2023 batch, with its status rules."""

    __tablename__ = "classes"
    __table_args__ = (
        UniqueConstraint("mentor_id", "name"),
        CheckConstraint("attendance_threshold BETWEEN 1 AND 100", name="attendance_threshold"),
        CheckConstraint("midsem_max BETWEEN 1 AND 100", name="midsem_max"),
        CheckConstraint("midsem_pass_mark BETWEEN 0 AND midsem_max", name="midsem_pass_mark"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    mentor_id: Mapped[int] = mapped_column(ForeignKey("mentors.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(40))
    department: Mapped[str] = mapped_column(String(80))
    admission_year: Mapped[int]
    attendance_threshold: Mapped[int] = mapped_column(default=75, server_default="75")
    midsem_pass_mark: Mapped[int] = mapped_column(default=7, server_default="7")
    midsem_max: Mapped[int] = mapped_column(default=20, server_default="20")
    # Set by the mentor once the batch has left; the class then moves to Past batches.
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    # The database deletes children through ON DELETE CASCADE; passive_deletes stops the
    # ORM loading every row first.
    semesters: Mapped[list["Semester"]] = relationship(
        back_populates="class_group",
        order_by="Semester.number",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    students: Mapped[list["Student"]] = relationship(
        back_populates="class_group", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<ClassGroup {self.id} {self.name}>"


class Semester(db.Model):
    __tablename__ = "semesters"
    __table_args__ = (
        UniqueConstraint("class_id", "number"),
        CheckConstraint(f"number BETWEEN {MIN_SEMESTER} AND {MAX_SEMESTER}", name="number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"))
    number: Mapped[int]
    # Rounds count imports, so "pending" never depends on comparing timestamps (see
    # ARCHITECTURE.md decision 8). Both stay 0 until the first import.
    current_round: Mapped[int] = mapped_column(default=0, server_default="0")
    round_counter: Mapped[int] = mapped_column(default=0, server_default="0")
    last_imported_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=lambda: clock.now())

    class_group: Mapped[ClassGroup] = relationship(back_populates="semesters")
    students: Mapped[list["Student"]] = relationship(
        secondary=semester_students, back_populates="semesters", passive_deletes=True
    )
    subjects: Mapped[list["SemesterSubject"]] = relationship(
        order_by="SemesterSubject.position", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Semester {self.id} class={self.class_id} number={self.number}>"


class Student(Timestamps, db.Model):
    """A student of a class. Name, parent and phone carry over between semesters."""

    __tablename__ = "students"
    __table_args__ = (
        UniqueConstraint("class_id", "enrollment_no"),
        CheckConstraint(
            "status IN ({})".format(", ".join(f"'{status}'" for status in STUDENT_STATUSES)),
            name="status",
        ),
        CheckConstraint("gender IN ('male', 'female')", name="gender"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"))
    enrollment_no: Mapped[str] = mapped_column(String(30))
    full_name: Mapped[str] = mapped_column(String(120))
    parent_name: Mapped[str] = mapped_column(String(120), default="", server_default="")
    phone_raw: Mapped[str] = mapped_column(String(40), default="", server_default="")
    # None when the sheet's number is not a valid Indian mobile; the student is then
    # listed but cannot be messaged until the number is fixed.
    phone_e164: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(10), default="active", server_default="active")
    # "male" or "female", so the message says "your son" or "your daughter"; None says
    # "your ward".
    gender: Mapped[str | None] = mapped_column(String(6))

    class_group: Mapped[ClassGroup] = relationship(back_populates="students")
    semesters: Mapped[list[Semester]] = relationship(
        secondary=semester_students, back_populates="students", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Student {self.id} {self.enrollment_no}>"


class SemesterSubject(db.Model):
    """A subject column of a semester's sheet, kept in the sheet's order."""

    __tablename__ = "semester_subjects"
    __table_args__ = (UniqueConstraint("semester_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    semester_id: Mapped[int] = mapped_column(ForeignKey("semesters.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(80))
    position: Mapped[int]


class Result(db.Model):
    """One student's numbers in one subject. None means no data yet."""

    __tablename__ = "results"
    __table_args__ = (
        UniqueConstraint("semester_subject_id", "student_id"),
        CheckConstraint("theory_pct BETWEEN 0 AND 100", name="theory_pct"),
        CheckConstraint("practical_pct BETWEEN 0 AND 100", name="practical_pct"),
        CheckConstraint("midsem_marks >= 0", name="midsem_marks"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    semester_subject_id: Mapped[int] = mapped_column(
        ForeignKey("semester_subjects.id", ondelete="CASCADE")
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True
    )
    theory_pct: Mapped[float | None]
    practical_pct: Mapped[float | None]
    midsem_marks: Mapped[float | None]
    midsem_absent: Mapped[bool] = mapped_column(default=False, server_default=false())


class SemesterStats(db.Model):
    """A semester's counts, kept so pages across many classes stay quick. Any change that
    affects them clears the row, and a row older than half an hour is worked out again."""

    __tablename__ = "semester_stats"

    semester_id: Mapped[int] = mapped_column(
        ForeignKey("semesters.id", ondelete="CASCADE"), primary_key=True
    )
    students: Mapped[int]
    at_risk: Mapped[int]
    pending: Mapped[int]
    computed_at: Mapped[datetime] = mapped_column(UTCDateTime)
