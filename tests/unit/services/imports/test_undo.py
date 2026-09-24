import pytest
from sqlalchemy import func, select

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import Result, SemesterSubject, Student
from parent_notifier.services.imports import undo
from parent_notifier.services.imports.apply import apply_import
from parent_notifier.services.imports.sheet_parser import parse_sheet
from tests.factories.academics import make_class, make_semester
from tests.factories.accounts import make_mentor

pytestmark = pytest.mark.usefixtures("app_context")

HEADER = ["Enrollment No", "Student Name", "Parent Name", "Parent Phone", "DBMS"]
AVI = ["23CE001", "Avi Shah", "Mehul Shah", "9000000101"]
RIYA = ["23CE002", "Riya Patel", "Kiran Patel", "9000000102"]


@pytest.fixture
def setup():
    mentor = make_mentor()
    class_group = make_class(mentor)
    return mentor, class_group, make_semester(class_group, 4)


def _import(setup, rows, header=HEADER, update_identity=False, semester=None):
    mentor, class_group, default = setup
    sheet = parse_sheet([header, *rows], 20)
    apply_import(class_group, semester or default, mentor.id, "s.xlsx", sheet, update_identity)


def _state(semester):
    results = db.session.execute(
        select(Student.enrollment_no, SemesterSubject.name, Result.theory_pct)
        .join(Result, Result.student_id == Student.id)
        .join(SemesterSubject, Result.semester_subject_id == SemesterSubject.id)
        .where(SemesterSubject.semester_id == semester.id)
        .order_by(Student.enrollment_no, SemesterSubject.name)
    ).all()
    subjects = [subject.name for subject in semester.subjects]
    members = sorted(student.enrollment_no for student in semester.students)
    return subjects, members, [tuple(row) for row in results]


def _undo(semester):
    batch = undo.latest_undoable(semester)
    assert batch is not None
    undo.undo_import(semester, batch)


def test_undoing_the_only_import_empties_the_semester(setup):
    _, _, semester = setup
    _import(setup, [[*AVI, "Theory=80"]])
    _undo(semester)
    assert _state(semester) == ([], [], [])
    assert db.session.scalar(select(func.count()).select_from(Student)) == 0
    assert (semester.current_round, semester.round_counter) == (0, 1)
    assert semester.last_imported_at is None


def test_undoing_a_reimport_restores_the_state_before_it(setup):
    _, _, semester = setup
    _import(setup, [[*AVI, "Theory=80"]])
    before = _state(semester)
    _import(
        setup, [[*AVI, "Theory=90", "Theory=70"], [*RIYA, "Theory=60", ""]], header=[*HEADER, "OS"]
    )
    _undo(semester)
    assert _state(semester) == before
    assert semester.current_round == 1


def test_identity_changes_are_put_back(setup):
    _, _, semester = setup
    _import(setup, [[*AVI, "Theory=80"]])
    _import(setup, [["23CE001", "Avi M. Shah", "", "9000000199", ""]], update_identity=True)
    _undo(semester)
    student = db.session.scalar(select(Student))
    assert (student.full_name, student.phone_e164) == ("Avi Shah", "+919000000101")


def test_only_the_latest_import_can_be_undone_and_only_once(setup):
    _, _, semester = setup
    _import(setup, [[*AVI, "Theory=80"]])
    _import(setup, [[*AVI, "Theory=85"]])
    _undo(semester)
    assert undo.latest_undoable(semester) is None


def test_students_listed_in_another_semester_are_kept(setup):
    _, class_group, sem4 = setup
    sem5 = make_semester(class_group, 5)
    _import(setup, [[*AVI, "Theory=80"]])
    _import(setup, [[*AVI, "Theory=70"]], semester=sem5)
    _undo(sem4)
    assert [student.enrollment_no for student in sem5.students] == ["23CE001"]


def test_a_student_deleted_after_a_reimport_stays_deleted_on_undo(setup):
    _, _, semester = setup
    _import(setup, [[*AVI, "Theory=80"], [*RIYA, "Theory=70"]])
    _import(setup, [[*AVI, "Theory=90"], [*RIYA, "Theory=75"]])
    riya = db.session.scalars(select(Student).filter_by(enrollment_no="23CE002")).one()
    db.session.delete(riya)
    db.session.commit()
    _undo(semester)
    assert _state(semester) == (["DBMS"], ["23CE001"], [("23CE001", "DBMS", 80)])
