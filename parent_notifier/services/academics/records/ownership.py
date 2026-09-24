"""Queries scoped to one mentor. Another mentor's records are simply not found, and
routes answer 404 rather than 403 so an id reveals nothing about who owns it."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup, Semester, Student


@dataclass(frozen=True)
class ClassRow:
    """One line of the classes list."""

    class_group: ClassGroup
    latest_semester: int | None
    active_students: int
    last_imported_at: datetime | None


def get_class(mentor_id: int, class_id: int) -> ClassGroup | None:
    return db.session.scalar(
        select(ClassGroup).where(ClassGroup.id == class_id, ClassGroup.mentor_id == mentor_id)
    )


def class_links(mentor_id: int) -> list[tuple[int, str]]:
    """Id and name of each class, for the navigation pane."""
    query = (
        select(ClassGroup.id, ClassGroup.name)
        .where(ClassGroup.mentor_id == mentor_id)
        .order_by(func.lower(ClassGroup.name))
    )
    return [(row.id, row.name) for row in db.session.execute(query)]


def _over_semesters(expression):
    return select(expression).where(Semester.class_id == ClassGroup.id).scalar_subquery()


def list_classes(mentor_id: int) -> list[ClassRow]:
    """Every class of the mentor with its latest semester, active students and last
    import, in one query however many classes there are."""
    active_students = (
        select(func.count(Student.id))
        .where(Student.class_id == ClassGroup.id, Student.status == "active")
        .scalar_subquery()
    )
    query = (
        select(
            ClassGroup,
            _over_semesters(func.max(Semester.number)),
            active_students,
            _over_semesters(func.max(Semester.last_imported_at)),
        )
        .where(ClassGroup.mentor_id == mentor_id)
        .order_by(func.lower(ClassGroup.name))
    )
    return [ClassRow(*row) for row in db.session.execute(query)]
