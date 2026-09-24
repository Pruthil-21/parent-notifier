"""Search from the top bar: classes and students, and for the admin every mentor too.

A mentor finds only their own classes and students. The admin finds every class and
student; those of other mentors open in the read-only view.
"""

from dataclasses import dataclass

from sqlalchemy import func, or_, select

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup, Semester, Student, semester_students
from parent_notifier.models.accounts import Mentor
from parent_notifier.services.admin.overview import phone_digits

MIN_LENGTH = 2
MAX_LENGTH = 80
# Matches shown per group; a longer list asks for a narrower search instead.
LIMIT = 20


@dataclass(frozen=True)
class ClassHit:
    id: int
    name: str
    department: str
    admission_year: int
    own: bool


@dataclass(frozen=True)
class StudentHit:
    id: int
    name: str
    enrollment_no: str
    status: str
    class_id: int
    class_name: str
    # The latest semester the student is in, where their page opens; None before any.
    semester: int | None
    own: bool


@dataclass(frozen=True)
class Group:
    hits: list
    more: bool  # more matches than LIMIT


@dataclass(frozen=True)
class Results:
    classes: Group
    students: Group
    mentors: Group | None  # the admin's only

    @property
    def empty(self) -> bool:
        groups = (self.classes, self.students, self.mentors)
        return not any(group.hits for group in groups if group is not None)


def clean(value: str | None) -> str:
    return " ".join((value or "").split())[:MAX_LENGTH]


def _contains(column, text: str):
    # autoescape: a typed % or _ is a character to find, not a wildcard.
    return func.lower(column).contains(text.lower(), autoescape=True)


def _group(rows: list, make) -> Group:
    return Group([make(row) for row in rows[:LIMIT]], more=len(rows) > LIMIT)


def _classes(text: str, viewer: Mentor, scope: list) -> Group:
    query = (
        select(ClassGroup)
        .where(
            *scope, or_(_contains(ClassGroup.name, text), _contains(ClassGroup.department, text))
        )
        .order_by(func.lower(ClassGroup.name), ClassGroup.id)
        .limit(LIMIT + 1)
    )
    return _group(
        list(db.session.scalars(query)),
        lambda c: ClassHit(c.id, c.name, c.department, c.admission_year, c.mentor_id == viewer.id),
    )


def _students(text: str, digits: str | None, viewer: Mentor, scope: list) -> Group:
    latest = (
        select(func.max(Semester.number))
        .join(semester_students, semester_students.c.semester_id == Semester.id)
        .where(semester_students.c.student_id == Student.id)
        .correlate(Student)
        .scalar_subquery()
    )
    matches = [
        _contains(Student.full_name, text),
        _contains(Student.enrollment_no, text),
        _contains(Student.parent_name, text),
    ]
    if digits:
        matches.append(Student.phone_e164.contains(digits, autoescape=True))
    query = (
        select(Student, ClassGroup.name, ClassGroup.mentor_id, latest)
        .join(ClassGroup, Student.class_id == ClassGroup.id)
        .where(*scope, or_(*matches))
        .order_by(func.lower(Student.full_name), Student.id)
        .limit(LIMIT + 1)
    )

    def hit(row) -> StudentHit:
        student, class_name, mentor_id, semester = row
        return StudentHit(
            student.id,
            student.full_name,
            student.enrollment_no,
            student.status,
            student.class_id,
            class_name,
            semester,
            mentor_id == viewer.id,
        )

    return _group(list(db.session.execute(query)), hit)


def _mentors(text: str, digits: str | None) -> Group:
    matches = [
        _contains(Mentor.full_name, text),
        _contains(Mentor.username, text),
        _contains(Mentor.department, text),
    ]
    if digits:
        matches.append(Mentor.whatsapp_number.contains(digits, autoescape=True))
    query = (
        select(Mentor)
        .where(Mentor.approved.is_(True), or_(*matches))
        .order_by(func.lower(Mentor.full_name), Mentor.id)
        .limit(LIMIT + 1)
    )
    return _group(list(db.session.scalars(query)), lambda mentor: mentor)


def run(text: str, viewer: Mentor) -> Results | None:
    """None when the search is too short to be useful."""
    if len(text) < MIN_LENGTH:
        return None
    digits = phone_digits(text)
    scope = [] if viewer.is_admin else [ClassGroup.mentor_id == viewer.id]
    return Results(
        classes=_classes(text, viewer, scope),
        students=_students(text, digits, viewer, scope),
        mentors=_mentors(text, digits) if viewer.is_admin else None,
    )
