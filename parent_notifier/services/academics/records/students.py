"""Adding a student by hand, editing their details and one semester's figures, marking
them left or detained, and deleting them."""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup, Result, Semester, Student
from parent_notifier.models.messaging import SendLog
from parent_notifier.services.academics.views import semester_stats
from parent_notifier.services.imports.cell_parser import SubjectCell
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


def results_of(semester: Semester, student: Student) -> dict[int, Result]:
    """The student's saved figures in this semester, by subject id."""
    ids = [subject.id for subject in semester.subjects]
    query = select(Result).where(
        Result.student_id == student.id, Result.semester_subject_id.in_(ids)
    )
    return {result.semester_subject_id: result for result in db.session.scalars(query)}


def _set_results(semester: Semester, student: Student, cells: dict[int, SubjectCell]) -> None:
    """Replace the figures of each subject given, by subject id. A subject left empty has
    no figures at all, as before any sheet; the caller commits."""
    saved = results_of(semester, student)
    for subject in semester.subjects:
        if subject.id not in cells:
            continue
        cell, result = cells[subject.id], saved.get(subject.id)
        if cell.is_empty:
            if result is not None:
                db.session.delete(result)
            continue
        if result is None:
            result = Result(semester_subject_id=subject.id, student_id=student.id)
            db.session.add(result)
        result.theory_pct, result.practical_pct = cell.theory, cell.practical
        result.midsem_marks, result.midsem_absent = cell.marks, cell.absent


def add_student(
    class_group: ClassGroup,
    semester: Semester,
    enrollment_no: str,
    details: dict,
    cells: dict[int, SubjectCell] | None = None,
) -> Student:
    """Add to the class and to this semester, with any figures typed for it."""
    student = Student(class_id=class_group.id, enrollment_no=enrollment_no)
    _set_details(student, details)
    semester.students.append(student)
    try:
        semester_stats.invalidate(semester.id)  # flushes, so a taken number fails here
        _set_results(semester, student, cells or {})
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise EnrollmentTakenError(enrollment_no) from None
    return student


def update_student(
    student: Student,
    details: dict,
    semester: Semester | None = None,
    cells: dict[int, SubjectCell] | None = None,
) -> None:
    _set_details(student, details)
    if semester is not None:
        _set_results(semester, student, cells or {})
    semester_stats.invalidate_class(student.class_id)
    db.session.commit()


def _set_details(student: Student, details: dict) -> None:
    student.full_name = details["full_name"]
    student.parent_name = details["parent_name"]
    student.phone_raw = details["phone"]
    student.phone_e164 = normalise_indian_mobile(details["phone"])
    student.status = details["status"]
    student.gender = details.get("gender")


def messages_sent(student: Student) -> int:
    """How many messages this student's parent was sent, which deleting also removes."""
    query = select(func.count()).where(SendLog.student_id == student.id, SendLog.status == "sent")
    return db.session.scalar(query)


def delete_student(student: Student) -> None:
    """Delete the student with their marks in every semester and their send record. The
    database removes those rows through its foreign keys."""
    semester_stats.invalidate_class(student.class_id)
    db.session.delete(student)
    db.session.commit()
