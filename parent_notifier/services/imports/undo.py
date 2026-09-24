"""Undoing the most recent import of a semester by restoring its snapshot."""

from datetime import date, datetime

from sqlalchemy import delete, exists, select

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import (
    Result,
    Semester,
    SemesterSubject,
    Student,
    semester_students,
)
from parent_notifier.models.imports import ImportBatch
from parent_notifier.services.academics.views import semester_stats
from parent_notifier.services.imports.apply import IDENTITY_FIELDS
from parent_notifier.services.shared import clock


def latest_undoable(semester: Semester) -> ImportBatch | None:
    """Only the latest import, only once, and only while it is still the current round."""
    batch = db.session.scalar(
        select(ImportBatch)
        .where(ImportBatch.semester_id == semester.id)
        .order_by(ImportBatch.id.desc())
        .limit(1)
    )
    if batch is None or batch.undone_at is not None or batch.round != semester.current_round:
        return None
    return batch


def _restore_results(semester: Semester, snapshot: dict) -> None:
    kept = {subject["id"]: subject for subject in snapshot["subjects"]}
    for subject in list(semester.subjects):
        if subject.id not in kept:
            semester.subjects.remove(subject)  # its results go with it
        elif "midsem_max" in kept[subject.id]:
            subject.midsem_max = kept[subject.id]["midsem_max"]
    subject_ids = select(SemesterSubject.id).where(SemesterSubject.semester_id == semester.id)
    db.session.execute(delete(Result).where(Result.semester_subject_id.in_(subject_ids)))
    # A student deleted since the import stays deleted: their saved marks are skipped.
    saved_ids = {values["student_id"] for values in snapshot["results"]}
    existing = set(db.session.scalars(select(Student.id).where(Student.id.in_(saved_ids))))
    db.session.add_all(
        Result(**values) for values in snapshot["results"] if values["student_id"] in existing
    )


def _restore_identities(snapshot: dict) -> None:
    for saved in snapshot["identities"]:
        student = db.session.get(Student, saved["id"])
        if student is not None:
            for name in IDENTITY_FIELDS:
                setattr(student, name, saved[name])


def _remove_created_students(snapshot: dict) -> None:
    """Students this import added go, unless another semester lists them too."""
    for student_id in snapshot["created_student_ids"]:
        listed = db.session.scalar(
            select(exists().where(semester_students.c.student_id == student_id))
        )
        student = db.session.get(Student, student_id)
        if student is not None and not listed:
            db.session.delete(student)


def undo_import(semester: Semester, batch: ImportBatch) -> None:
    snapshot = batch.snapshot
    _restore_results(semester, snapshot)
    member_ids = set(snapshot["student_ids"])
    semester.students = [student for student in semester.students if student.id in member_ids]
    db.session.flush()
    _restore_identities(snapshot)
    _remove_created_students(snapshot)
    semester.current_round = batch.previous_round
    last = snapshot["last_imported_at"]
    semester.last_imported_at = datetime.fromisoformat(last) if last else None
    # Imports saved before the dates existed keep whatever dates the semester has.
    for name in ("attendance_from", "attendance_to"):
        if name in snapshot:
            value = snapshot[name]
            setattr(semester, name, date.fromisoformat(value) if value else None)
    batch.undone_at = clock.now()
    semester_stats.invalidate_class(semester.class_id)
    db.session.commit()
