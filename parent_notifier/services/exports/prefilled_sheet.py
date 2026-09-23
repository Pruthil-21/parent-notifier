"""A semester's sheet filled in with its students and current numbers, ready to update
and upload again. With no import yet it lists the class's active students."""

from sqlalchemy import select

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup, Result, Semester, SemesterSubject, Student
from parent_notifier.services.exports.workbook_style import (
    IDENTITY_HEADERS,
    add_row,
    new_sheet,
    to_bytes,
)
from parent_notifier.services.imports.cell_parser import SubjectCell, format_cell


def _students(class_group: ClassGroup, semester: Semester) -> list[Student]:
    students = semester.students or [s for s in class_group.students if s.status == "active"]
    return sorted(students, key=lambda student: student.enrollment_no)


def _cells(semester: Semester) -> dict[tuple[int, int], str]:
    query = (
        select(Result)
        .join(SemesterSubject, Result.semester_subject_id == SemesterSubject.id)
        .where(SemesterSubject.semester_id == semester.id)
    )
    return {
        (result.student_id, result.semester_subject_id): format_cell(
            SubjectCell(
                theory=result.theory_pct,
                practical=result.practical_pct,
                marks=result.midsem_marks,
                absent=result.midsem_absent,
            )
        )
        for result in db.session.scalars(query)
    }


def prefilled_sheet(class_group: ClassGroup, semester: Semester) -> bytes:
    subjects = semester.subjects
    title = f"{class_group.name} Sem {semester.number}"
    workbook, sheet = new_sheet(title, IDENTITY_HEADERS + [subject.name for subject in subjects])
    cells = _cells(semester)
    for student in _students(class_group, semester):
        identity = [
            student.enrollment_no,
            student.full_name,
            student.parent_name,
            student.phone_raw,
        ]
        add_row(sheet, identity + [cells.get((student.id, s.id), "") for s in subjects])
    return to_bytes(workbook)
