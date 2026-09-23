"""Creating and changing a mentor's classes."""

from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup


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


def _commit_or_name_taken(name: str) -> None:
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ClassNameTakenError(name) from None
