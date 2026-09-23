import pytest
from sqlalchemy import select

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import Semester, Student
from tests.factories.academics import make_class, make_semester, make_student
from tests.factories.accounts import make_mentor

NEW = {
    "enrollment_no": " 23CE050 ",
    "full_name": "Tanvi   Shah",
    "parent_name": "Mehul Shah",
    "phone": "90000 00150",
    "status": "active",
}


@pytest.fixture
def setup(app, mentor):
    with app.app_context():
        class_group = make_class(mentor)
        semester = make_semester(class_group, 4)
        student = make_student(class_group, "23CE001", phone_raw="123", phone_e164=None)
        semester.students.append(student)
        db.session.commit()
        return f"/classes/{class_group.id}/sem/4", student.id


def _student(app, enrollment):
    with app.app_context():
        return db.session.scalar(select(Student).where(Student.enrollment_no == enrollment))


def test_semester_page_offers_add_and_edit(signed_in_client, setup):
    base, student_id = setup
    html = signed_in_client.get(base).get_data(as_text=True)
    assert f'href="{base}/students/new"' in html
    assert f'data-edit-url="{base}/students/{student_id}/edit"' in html
    assert "data-popup-edit" in html


def test_adding_puts_the_student_in_class_and_semester(app, signed_in_client, setup):
    base, _ = setup
    response = signed_in_client.post(f"{base}/students/new", data=NEW, follow_redirects=True)
    assert "Tanvi Shah added to Sem 4." in response.get_data(as_text=True)
    student = _student(app, "23CE050")
    assert (student.full_name, student.phone_e164) == ("Tanvi Shah", "+919000000150")
    with app.app_context():
        semester = db.session.scalar(select(Semester))
        assert "23CE050" in [s.enrollment_no for s in semester.students]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("enrollment_no", "", "Enter the enrollment number"),
        ("enrollment_no", "23ce001", "Another student in this class has this enrollment number"),
        ("full_name", "", "Enter the student&#39;s name"),
        ("phone", "", "Enter the parent&#39;s mobile number"),
        ("phone", "12345", "Enter a 10-digit mobile number, like 98765 43210"),
        ("status", "graduated", "Not a valid choice"),
    ],
)
def test_add_problems_are_explained(app, signed_in_client, setup, field, value, message):
    base, _ = setup
    html = signed_in_client.post(f"{base}/students/new", data=NEW | {field: value}).get_data(
        as_text=True
    )
    assert "There is a problem" in html
    assert message in html
    assert _student(app, "23CE050") is None


def test_editing_fixes_details_and_marks_status(app, signed_in_client, setup):
    base, student_id = setup
    page = signed_in_client.get(f"{base}/students/{student_id}/edit").get_data(as_text=True)
    assert 'value="123"' in page
    assert "cannot be changed" in page
    data = {"full_name": "Avi M. Shah", "parent_name": "", "phone": "9000000199", "status": "left"}
    response = signed_in_client.post(f"{base}/students/{student_id}/edit", data=data)
    assert response.headers["Location"] == base
    student = _student(app, "23CE001")
    assert (student.full_name, student.phone_e164, student.status) == (
        "Avi M. Shah",
        "+919000000199",
        "left",
    )


def test_enrollment_number_cannot_be_changed(app, signed_in_client, setup):
    base, student_id = setup
    data = {"enrollment_no": "HACK", "full_name": "Avi", "phone": "9000000101", "status": "active"}
    signed_in_client.post(f"{base}/students/{student_id}/edit", data=data)
    assert _student(app, "23CE001") is not None
    assert _student(app, "HACK") is None


def test_another_mentors_student_cannot_be_edited(app, signed_in_client, setup):
    base, _ = setup
    with app.app_context():
        stranger = make_mentor(username="niravshah", whatsapp_number="+919000000002")
        other = make_student(make_class(stranger, name="IT-B"), "23IT001")
        other_id = other.id
    data = {"full_name": "Hacked", "phone": "9000000101", "status": "left"}
    assert signed_in_client.post(f"{base}/students/{other_id}/edit", data=data).status_code == 404
    assert _student(app, "23IT001").full_name != "Hacked"


@pytest.mark.parametrize("path", ["students/new", "students/1/edit"])
def test_student_forms_need_sign_in(client, setup, path):
    base, _ = setup
    assert client.get(f"{base}/{path}").headers["Location"].startswith("/sign-in")
