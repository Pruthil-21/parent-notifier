import pytest

from parent_notifier.core.extensions import db
from parent_notifier.services.academics import semesters
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
