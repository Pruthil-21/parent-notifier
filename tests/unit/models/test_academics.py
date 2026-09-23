import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup, Semester, Student, semester_students
from tests.factories.academics import make_class, make_semester, make_student
from tests.factories.accounts import make_mentor

pytestmark = pytest.mark.usefixtures("app_context")


@pytest.fixture
def owner():
    return make_mentor()


def _count(table) -> int:
    return db.session.scalar(select(func.count()).select_from(table))


def test_new_class_gets_the_default_status_rules(owner):
    class_group = make_class(owner)
    rules = (class_group.attendance_threshold, class_group.midsem_pass_mark)
    assert rules == (75, 7)
    assert class_group.midsem_max == 20


def test_class_names_are_unique_per_mentor_only(owner):
    make_class(owner, name="CE-A")
    other = make_mentor(username="niravshah", whatsapp_number="+919000000002")
    assert make_class(other, name="CE-A").id
    with pytest.raises(IntegrityError):
        make_class(owner, name="CE-A")


@pytest.mark.parametrize(
    "fields",
    [
        {"attendance_threshold": 0},
        {"attendance_threshold": 101},
        {"midsem_max": 0},
        {"midsem_pass_mark": 21},
        {"midsem_pass_mark": -1},
    ],
)
def test_database_rejects_impossible_rules(owner, fields):
    with pytest.raises(IntegrityError):
        make_class(owner, **fields)
    db.session.rollback()


@pytest.mark.parametrize("number", [0, 13])
def test_semester_numbers_stay_between_1_and_12(owner, number):
    class_group = make_class(owner)
    with pytest.raises(IntegrityError):
        make_semester(class_group, number)
    db.session.rollback()


def test_each_semester_number_appears_once_per_class(owner):
    class_group = make_class(owner)
    make_semester(class_group, 3)
    with pytest.raises(IntegrityError):
        make_semester(class_group, 3)


def test_semesters_are_listed_in_order(owner):
    class_group = make_class(owner)
    for number in (4, 1, 3):
        make_semester(class_group, number)
    db.session.expire_all()
    assert [semester.number for semester in class_group.semesters] == [1, 3, 4]


def test_new_semester_starts_with_no_imports(owner):
    semester = make_semester(make_class(owner))
    assert (semester.current_round, semester.round_counter) == (0, 0)
    assert semester.last_imported_at is None


def test_enrollment_numbers_are_unique_per_class(owner):
    class_group = make_class(owner)
    make_student(class_group, "23CE001")
    with pytest.raises(IntegrityError):
        make_student(class_group, "23CE001")


def test_student_status_is_limited(owner):
    class_group = make_class(owner)
    assert make_student(class_group).status == "active"
    with pytest.raises(IntegrityError):
        make_student(class_group, "23CE002", status="graduated")


def test_deleting_a_class_removes_everything_under_it(owner):
    class_group = make_class(owner)
    semester = make_semester(class_group)
    student = make_student(class_group)
    semester.students.append(student)
    db.session.commit()
    db.session.delete(class_group)
    db.session.commit()
    for table in (ClassGroup, Semester, Student, semester_students):
        assert _count(table) == 0


def test_deleting_a_mentor_removes_their_classes(owner):
    make_semester(make_class(owner))
    db.session.delete(owner)
    db.session.commit()
    assert _count(ClassGroup) == 0
    assert _count(Semester) == 0
