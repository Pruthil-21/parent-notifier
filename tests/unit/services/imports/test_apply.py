import pytest
from sqlalchemy import func, select

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import Result, SemesterSubject, Student
from parent_notifier.models.imports import ImportBatch
from parent_notifier.services.imports.apply import apply_import
from parent_notifier.services.imports.sheet_parser import parse_sheet
from tests.factories.academics import make_class, make_semester
from tests.factories.accounts import make_mentor

pytestmark = pytest.mark.usefixtures("app_context")

HEADER = ["Enrollment No", "Student Name", "Parent Name", "Parent Phone", "DBMS", "OS"]
AVI = ["23CE001", "Avi Shah", "Mehul Shah", "9000000101"]
RIYA = ["23CE002", "Riya Patel", "Kiran Patel", "9000000102"]


@pytest.fixture
def setup():
    mentor = make_mentor()
    class_group = make_class(mentor)
    return mentor, class_group, make_semester(class_group, 4)


def _import(setup, rows, header=HEADER, update_identity=False, semester=None):
    mentor, class_group, default_semester = setup
    sheet = parse_sheet([header, *rows], class_group.midsem_max)
    assert sheet.errors == []
    target = semester or default_semester
    return apply_import(class_group, target, mentor.id, "s.xlsx", sheet, update_identity)


def _result(enrollment_no, subject) -> Result | None:
    query = (
        select(Result)
        .join(Student, Result.student_id == Student.id)
        .join(SemesterSubject, Result.semester_subject_id == SemesterSubject.id)
        .where(Student.enrollment_no == enrollment_no, SemesterSubject.name == subject)
    )
    return db.session.scalar(query)


def _count(model) -> int:
    return db.session.scalar(select(func.count()).select_from(model))


def test_first_import_saves_students_subjects_and_results(setup):
    _, _, semester = setup
    outcome = _import(setup, [[*AVI, "Theory=86,Practical=92,Marks=16", "Theory=79,Marks=AB"]])
    assert (outcome.added, outcome.updated) == (1, 0)
    assert [subject.name for subject in semester.subjects] == ["DBMS", "OS"]
    assert [student.enrollment_no for student in semester.students] == ["23CE001"]
    dbms, os_ = _result("23CE001", "DBMS"), _result("23CE001", "OS")
    assert (dbms.theory_pct, dbms.practical_pct, dbms.midsem_marks) == (86, 92, 16)
    assert (os_.theory_pct, os_.midsem_marks, os_.midsem_absent) == (79, None, True)
    assert (semester.round_counter, semester.current_round) == (1, 1)
    assert semester.last_imported_at is not None


def test_import_is_recorded_with_a_snapshot_of_before(setup):
    _import(setup, [[*AVI, "Theory=86", ""]])
    _import(setup, [[*AVI, "Theory=90", ""], [*RIYA, "", ""]])
    first, second = db.session.scalars(select(ImportBatch).order_by(ImportBatch.id)).all()
    assert (first.round, first.previous_round, first.added_count) == (1, 0, 1)
    assert first.snapshot["results"] == []
    assert (second.round, second.previous_round) == (2, 1)
    assert (second.added_count, second.updated_count) == (1, 1)
    assert second.snapshot["results"][0]["theory_pct"] == 86
    assert len(second.snapshot["created_student_ids"]) == 1


def test_reimport_updates_in_place_and_blank_keeps_saved_values(setup):
    _import(setup, [[*AVI, "Theory=86,Practical=92,Marks=16", "Theory=79"]])
    _import(setup, [[*AVI, "Theory=88", "Marks=12"]])
    dbms, os_ = _result("23CE001", "DBMS"), _result("23CE001", "OS")
    assert (dbms.theory_pct, dbms.practical_pct, dbms.midsem_marks) == (88, 92, 16)
    assert (os_.theory_pct, os_.midsem_marks) == (79, 12)
    assert _count(Student) == 1


def test_marks_after_absent_clear_the_absent_flag(setup):
    _import(setup, [[*AVI, "Marks=AB", ""]])
    _import(setup, [[*AVI, "Marks=9", ""]])
    dbms = _result("23CE001", "DBMS")
    assert (dbms.midsem_marks, dbms.midsem_absent) == (9, False)


def test_new_subjects_are_added_after_existing_ones(setup):
    _, _, semester = setup
    _import(setup, [[*AVI, "Theory=86", ""]])
    _import(setup, [[*AVI, "Theory=86", "Theory=70"]], header=[*HEADER[:4], "CN", "dbms"])
    assert [(s.name, s.position) for s in semester.subjects] == [
        ("DBMS", 0),
        ("OS", 1),
        ("CN", 2),
    ]


def test_empty_cells_do_not_create_result_rows(setup):
    _import(setup, [[*AVI, "Theory=86", ""]])
    assert _result("23CE001", "OS") is None


def test_identity_is_kept_unless_the_mentor_asks(setup):
    _import(setup, [[*AVI, "", ""]])
    changed = ["23ce001", "Avi M. Shah", "", "9000000199"]
    _import(setup, [[*changed, "", ""]])
    student = db.session.scalar(select(Student))
    assert (student.full_name, student.phone_e164) == ("Avi Shah", "+919000000101")
    _import(setup, [[*changed, "", ""]], update_identity=True)
    assert (student.full_name, student.parent_name) == ("Avi M. Shah", "Mehul Shah")
    assert student.phone_e164 == "+919000000199"


def test_students_carry_over_to_the_next_semester(setup):
    _, class_group, sem4 = setup
    _import(setup, [[*AVI, "Theory=80", ""]])
    sem5 = make_semester(class_group, 5)
    outcome = _import(setup, [[*AVI, "Theory=70", ""]], semester=sem5)
    assert (outcome.added, outcome.updated) == (0, 1)
    assert _count(Student) == 1
    assert sem5.students == sem4.students
