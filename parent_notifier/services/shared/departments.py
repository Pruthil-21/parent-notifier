"""The college's departments, used for mentors and classes alike.

Mentors and classes store a department's name. Renaming a department updates them all
in one transaction, and a department still in use cannot be removed.
"""

from sqlalchemy import func, select, update

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup
from parent_notifier.models.accounts import Mentor
from parent_notifier.models.college import Department


class DepartmentInUseError(Exception):
    """Mentors or classes still belong to the department."""


def names() -> list[str]:
    return list(db.session.scalars(select(Department.name).order_by(Department.name)))


def canonical(value: str | None) -> str | None:
    """The department as listed, whatever its case or spacing, or None if not listed."""
    wanted = " ".join((value or "").split()).lower()
    if not wanted:
        return None
    return db.session.scalar(select(Department.name).where(func.lower(Department.name) == wanted))


def usage(name: str) -> tuple[int, int]:
    """How many mentors and classes belong to the department."""
    mentors = db.session.scalar(select(func.count()).where(Mentor.department == name))
    classes = db.session.scalar(select(func.count()).where(ClassGroup.department == name))
    return mentors, classes


def add(name: str) -> Department:
    department = Department(name=name)
    db.session.add(department)
    db.session.commit()
    return department


def rename(department: Department, new_name: str) -> None:
    old = department.name
    department.name = new_name
    db.session.execute(update(Mentor).where(Mentor.department == old).values(department=new_name))
    db.session.execute(
        update(ClassGroup).where(ClassGroup.department == old).values(department=new_name)
    )
    db.session.commit()


def remove(department: Department) -> None:
    if any(usage(department.name)):
        raise DepartmentInUseError(department.name)
    db.session.delete(department)
    db.session.commit()


def listing() -> list[tuple[Department, int, int]]:
    """Each department with its mentor and class counts, in name order."""
    mentors = dict(
        db.session.execute(
            select(Mentor.department, func.count()).group_by(Mentor.department)
        ).all()
    )
    classes = dict(
        db.session.execute(
            select(ClassGroup.department, func.count()).group_by(ClassGroup.department)
        ).all()
    )
    listed = db.session.scalars(select(Department).order_by(Department.name))
    return [(d, mentors.get(d.name, 0), classes.get(d.name, 0)) for d in listed]


def get(department_id: int) -> Department | None:
    return db.session.get(Department, department_id)
