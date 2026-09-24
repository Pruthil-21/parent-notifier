"""Creating and changing a mentor's classes."""

from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup
from parent_notifier.services.academics.views import semester_stats
from parent_notifier.services.shared import clock


class ClassNameTakenError(Exception):
    """The mentor already has a class with this name."""


def name_taken(mentor_id: int, name: str, except_class_id: int | None = None) -> bool:
    """Names are compared ignoring case, so "CE-A" and "ce-a" cannot both exist."""
    query = exists().where(
        ClassGroup.mentor_id == mentor_id,
        func.lower(ClassGroup.name) == name.lower(),
        ClassGroup.id != (except_class_id or 0),
    )
    return db.session.scalar(select(query))


def create_class(mentor_id: int, name: str, department: str, admission_year: int) -> ClassGroup:
    class_group = ClassGroup(
        mentor_id=mentor_id, name=name, department=department, admission_year=admission_year
    )
    db.session.add(class_group)
    _commit_or_name_taken(name)
    return class_group


def update_details(
    class_group: ClassGroup, name: str, department: str, admission_year: int
) -> None:
    class_group.name = name
    class_group.department = department
    class_group.admission_year = admission_year
    _commit_or_name_taken(name)


def update_rules(
    class_group: ClassGroup, attendance_threshold: int, midsem_pass_mark: int, midsem_max: int
) -> None:
    """Values already validated by the form; the database refuses impossible ones too."""
    class_group.attendance_threshold = attendance_threshold
    class_group.midsem_pass_mark = midsem_pass_mark
    class_group.midsem_max = midsem_max
    semester_stats.invalidate_class(class_group.id)
    db.session.commit()


def finish(class_group: ClassGroup) -> None:
    """The batch has left. Nothing is removed and messages can still be sent."""
    class_group.finished_at = clock.now()
    db.session.commit()


def reopen(class_group: ClassGroup) -> None:
    class_group.finished_at = None
    db.session.commit()


def delete_class(class_group: ClassGroup) -> None:
    """Delete the class; the database removes its semesters and students with it."""
    db.session.delete(class_group)
    db.session.commit()


def _commit_or_name_taken(name: str) -> None:
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ClassNameTakenError(name) from None
