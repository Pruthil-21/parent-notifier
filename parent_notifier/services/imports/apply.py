"""Saving a reviewed sheet into a semester, in one transaction, with a snapshot for undo.

Identity (name, parent, phone) belongs to the class: a later sheet only changes it when
the mentor ticks "Update these details". A blank cell keeps whatever was saved before.
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import (
    ClassGroup,
    Result,
    Semester,
    SemesterSubject,
    Student,
)
from parent_notifier.models.imports import ImportBatch
from parent_notifier.services.academics.views import semester_stats
from parent_notifier.services.imports.cell_parser import SubjectCell
from parent_notifier.services.imports.compare import students_by_enrollment
from parent_notifier.services.imports.sheet_parser import ParsedSheet, SheetRow
from parent_notifier.services.shared import clock

IDENTITY_FIELDS = ("full_name", "parent_name", "phone_raw", "phone_e164")
RESULT_FIELDS = ("theory_pct", "practical_pct", "midsem_marks", "midsem_absent")


@dataclass(frozen=True)
class ImportOutcome:
    added: int
    updated: int


def _results(semester: Semester) -> dict[tuple[int, int], Result]:
    query = select(Result).join(SemesterSubject).where(SemesterSubject.semester_id == semester.id)
    return {
        (result.semester_subject_id, result.student_id): result
        for result in db.session.scalars(query)
    }


def take_snapshot(semester: Semester, students: list[Student]) -> dict:
    """What undo needs to restore the semester exactly, and the identities of students
    this import may change."""
    return {
        "subjects": [
            {
                "id": subject.id,
                "name": subject.name,
                "position": subject.position,
                "midsem_max": subject.midsem_max,
            }
            for subject in semester.subjects
        ],
        "student_ids": [student.id for student in semester.students],
        "results": [
            {"semester_subject_id": key[0], "student_id": key[1]}
            | {name: getattr(result, name) for name in RESULT_FIELDS}
            for key, result in _results(semester).items()
        ],
        "identities": [
            {"id": student.id} | {name: getattr(student, name) for name in IDENTITY_FIELDS}
            for student in students
        ],
        "current_round": semester.current_round,
        "last_imported_at": semester.last_imported_at.isoformat()
        if semester.last_imported_at
        else None,
        "attendance_from": _iso(semester.attendance_from),
        "attendance_to": _iso(semester.attendance_to),
    }


def _iso(day) -> str | None:
    return day.isoformat() if day else None


def _subjects(semester: Semester, sheet: ParsedSheet, class_max: int) -> dict:
    """Existing subjects are matched ignoring case; new ones are added after them. A
    subject with marks in the sheet takes their total; one without keeps its own."""
    names = sheet.subjects
    existing = {subject.name.lower(): subject for subject in semester.subjects}
    position = len(existing)
    found = {}
    for name in names:
        subject = existing.get(name.lower())
        if subject is None:
            subject = SemesterSubject(semester_id=semester.id, name=name, position=position)
            position += 1
            db.session.add(subject)
            semester.subjects.append(subject)
        if name in sheet.subject_max:
            total = sheet.subject_max[name]
            subject.midsem_max = None if total == class_max else total
        found[name] = subject
    db.session.flush()
    return found


def _merge(result: Result, cell: SubjectCell) -> None:
    """Only values present in the cell are written, so a blank keeps the saved value."""
    if cell.theory is not None:
        result.theory_pct = cell.theory
    if cell.practical is not None:
        result.practical_pct = cell.practical
    if cell.absent:
        result.midsem_marks, result.midsem_absent = None, True
    elif cell.marks is not None:
        result.midsem_marks, result.midsem_absent = cell.marks, False


def _student(class_group: ClassGroup, row: SheetRow) -> Student:
    student = Student(
        class_id=class_group.id,
        enrollment_no=row.enrollment_no,
        full_name=row.full_name,
        parent_name=row.parent_name,
        phone_raw=row.phone_raw,
        phone_e164=row.phone_e164,
    )
    db.session.add(student)
    return student


def _update_identity(student: Student, row: SheetRow) -> None:
    for name, value in (
        ("full_name", row.full_name),
        ("parent_name", row.parent_name),
        ("phone_raw", row.phone_raw),
    ):
        if value:
            setattr(student, name, value)
    if row.phone_raw:
        student.phone_e164 = row.phone_e164


def _apply_rows(class_group, semester, sheet, stored, update_identity) -> list[Student]:
    """Add or update every student and merge their results; return the students created."""
    subjects = _subjects(semester, sheet, class_group.midsem_max)
    results = _results(semester)
    members = set(semester.students)
    created = []
    for row in sheet.rows:
        student = stored.get(row.enrollment_no.upper())
        if student is None:
            student = _student(class_group, row)
            created.append(student)
            db.session.flush()  # the new student's id is needed for its results
        elif update_identity:
            _update_identity(student, row)
        if student not in members:
            semester.students.append(student)
            members.add(student)
        for name, cell in row.cells.items():
            key = (subjects[name].id, student.id)
            if key not in results:
                if cell.is_empty:
                    continue
                results[key] = Result(semester_subject_id=key[0], student_id=student.id)
                db.session.add(results[key])
            _merge(results[key], cell)
    return created


def apply_import(
    class_group: ClassGroup,
    semester: Semester,
    mentor_id: int,
    filename: str,
    sheet: ParsedSheet,
    update_identity: bool,
) -> ImportOutcome:
    """Everything happens in one transaction: either the whole sheet is saved with its
    snapshot, or nothing is."""
    stored = students_by_enrollment(class_group)
    in_sheet = [stored[key] for row in sheet.rows if (key := row.enrollment_no.upper()) in stored]
    snapshot = take_snapshot(semester, in_sheet if update_identity else [])
    created = _apply_rows(class_group, semester, sheet, stored, update_identity)
    outcome = ImportOutcome(added=len(created), updated=len(sheet.rows) - len(created))
    previous_round = semester.current_round
    semester.round_counter += 1
    semester.current_round = semester.round_counter
    semester.last_imported_at = clock.now()
    if sheet.attendance_from and sheet.attendance_to:
        semester.attendance_from = date.fromisoformat(sheet.attendance_from)
        semester.attendance_to = date.fromisoformat(sheet.attendance_to)
    db.session.add(
        ImportBatch(
            semester_id=semester.id,
            mentor_id=mentor_id,
            filename=filename,
            round=semester.current_round,
            previous_round=previous_round,
            added_count=outcome.added,
            updated_count=outcome.updated,
            snapshot=snapshot | {"created_student_ids": [student.id for student in created]},
        )
    )
    # Identity updates reach every semester of the class, so all their counts go.
    semester_stats.invalidate_class(class_group.id)
    db.session.commit()
    return outcome
