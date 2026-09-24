import pytest

from parent_notifier.core.extensions import db
from parent_notifier.services.academics.records import semesters
from tests.factories.academics import make_class, make_semester, make_student
from tests.factories.accounts import make_mentor

pytestmark = pytest.mark.usefixtures("app_context")


@pytest.fixture
def class_group():
    return make_class(make_mentor())


def test_adding_a_new_semester(class_group):
    semester, created = semesters.add_semester(class_group, 4)
    assert created
    assert (semester.class_id, semester.number) == (class_group.id, 4)


def test_adding_an_existing_semester_returns_it(class_group):
    existing = make_semester(class_group, 4)
    semester, created = semesters.add_semester(class_group, 4)
    assert not created
    assert semester == existing


def test_summaries_count_the_students_in_each_sheet(class_group):
    sem3 = make_semester(class_group, 3)
    make_semester(class_group, 4)
    first = make_student(class_group, "23CE001")
    second = make_student(class_group, "23CE002")
    sem3.students.extend([first, second])
    db.session.commit()
    summaries = semesters.summaries(class_group)
    assert [(summary.number, summary.students) for summary in summaries] == [(3, 2), (4, 0)]


def test_get_semester_only_looks_inside_the_class(class_group):
    make_semester(class_group, 2)
    other_class = make_class(make_mentor(username="niravshah", whatsapp_number="+919000000002"))
    assert semesters.get_semester(class_group, 2) is not None
    assert semesters.get_semester(other_class, 2) is None


def test_a_new_semester_is_empty_and_can_be_removed(class_group):
    semester = make_semester(class_group, 3)
    assert semesters.is_empty(semester)
    assert semesters.remove_if_empty(semester)
    assert semesters.get_semester(class_group, 3) is None


def test_a_semester_with_students_is_kept(class_group):
    semester = make_semester(class_group, 3)
    student = make_student(class_group)
    semester.students.append(student)
    db.session.commit()
    assert not semesters.remove_if_empty(semester)
    assert semesters.get_semester(class_group, 3) is not None


def test_a_semester_that_was_ever_imported_is_kept(class_group):
    semester = make_semester(class_group, 3, round_counter=1)
    assert not semesters.is_empty(semester)
    assert not semesters.remove_if_empty(semester)
