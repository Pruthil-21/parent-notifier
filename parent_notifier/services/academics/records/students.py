"""Adding a student by hand, editing their details and marking them left or detained."""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup, Semester, Student
from parent_notifier.services.shared.phone import normalise_indian_mobile


class EnrollmentTakenError(Exception):
    """Another student in the class already has this enrollment number."""


def get_student(class_group: ClassGroup, student_id: int) -> Student | None:
    """Only students of this class; other ids are simply not found."""
    return db.session.scalar(
        select(Student).where(Student.id == student_id, Student.class_id == class_group.id)
    )


def enrollment_taken(class_group: ClassGroup, enrollment_no: str) -> bool:
    query = select(Student.id).where(
        Student.class_id == class_group.id,
        func.upper(Student.enrollment_no) == enrollment_no.upper(),
    )
    return db.session.scalar(query) is not None


def add_student(
    class_group: ClassGroup, semester: Semester, enrollment_no: str, details: dict
) -> Student:
    """Add to the class and to this semester, with no numbers until a sheet has them."""
    student = Student(class_id=class_group.id, enrollment_no=enrollment_no)
    _set_details(student, details)
    semester.students.append(student)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise EnrollmentTakenError(enrollment_no) from None
    return student


def update_student(student: Student, details: dict) -> None:
    _set_details(student, details)
    db.session.commit()


def _set_details(student: Student, details: dict) -> None:
    student.full_name = details["full_name"]
    student.parent_name = details["parent_name"]
    student.phone_raw = details["phone"]
    student.phone_e164 = normalise_indian_mobile(details["phone"])
    student.status = details["status"]
