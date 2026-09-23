import pytest

from parent_notifier.services.academics import students
from tests.factories.academics import make_class, make_semester, make_student
from tests.factories.accounts import make_mentor

pytestmark = pytest.mark.usefixtures("app_context")

DETAILS = {"full_name": "Tanvi Shah", "parent_name": "", "phone": "90000 00150", "status": "active"}


@pytest.fixture
def class_group():
    return make_class(make_mentor())


def test_student_lookup_stays_inside_the_class(class_group):
    student = make_student(class_group)
    other_class = make_class(make_mentor(username="niravshah", whatsapp_number="+919000000002"))
    assert students.get_student(class_group, student.id) == student
    assert students.get_student(other_class, student.id) is None


def test_enrollment_numbers_are_compared_ignoring_case(class_group):
    make_student(class_group, "23CE001")
    assert students.enrollment_taken(class_group, "23ce001")
    assert not students.enrollment_taken(class_group, "23CE002")


def test_added_student_joins_the_semester_with_a_normalised_phone(class_group):
    semester = make_semester(class_group, 4)
    student = students.add_student(class_group, semester, "23CE050", DETAILS)
    assert student in semester.students
    assert student.phone_e164 == "+919000000150"


def test_duplicate_at_save_time_raises(class_group):
    make_student(class_group, "23CE050")
    semester = make_semester(class_group, 4)
    with pytest.raises(students.EnrollmentTakenError):
        students.add_student(class_group, semester, "23CE050", DETAILS)


def test_update_changes_details_and_status(class_group):
    student = make_student(class_group)
    students.update_student(student, DETAILS | {"phone": "123", "status": "detained"})
    assert (student.phone_e164, student.status) == (None, "detained")
