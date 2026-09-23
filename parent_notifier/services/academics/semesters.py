"""Adding semesters to a class and summarising them for the switcher."""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup, Semester, semester_students


@dataclass(frozen=True)
class SemesterSummary:
    number: int
    students: int


def get_semester(class_group: ClassGroup, number: int) -> Semester | None:
    return db.session.scalar(
        select(Semester).where(Semester.class_id == class_group.id, Semester.number == number)
    )


def summaries(class_group: ClassGroup) -> list[SemesterSummary]:
    """Each semester with how many students its sheet listed, lowest number first."""
    query = (
        select(Semester.number, func.count(semester_students.c.student_id))
        .outerjoin(semester_students, semester_students.c.semester_id == Semester.id)
        .where(Semester.class_id == class_group.id)
        .group_by(Semester.id)
        .order_by(Semester.number)
    )
    return [SemesterSummary(number, count) for number, count in db.session.execute(query)]


def add_semester(class_group: ClassGroup, number: int) -> tuple[Semester, bool]:
    """Add a semester, or return the existing one; the flag says whether it is new."""
    existing = get_semester(class_group, number)
    if existing:
        return existing, False
    semester = Semester(class_id=class_group.id, number=number)
    db.session.add(semester)
    try:
        db.session.commit()
    except IntegrityError:
        # Added in another tab at the same moment: open that one instead.
        db.session.rollback()
        return get_semester(class_group, number), False
    return semester, True
