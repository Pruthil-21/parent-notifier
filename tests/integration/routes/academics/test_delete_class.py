import pytest
from sqlalchemy import func, select

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup, Semester, Student
from tests.factories.academics import make_class, make_semester, make_student
from tests.factories.accounts import make_mentor


@pytest.fixture
def class_id(app, mentor):
    with app.app_context():
        class_group = make_class(mentor)
        semester = make_semester(class_group, 3)
        student = make_student(class_group)
        semester.students.append(student)
        db.session.commit()
        return class_group.id


@pytest.fixture
def strangers_class_id(app):
    with app.app_context():
        stranger = make_mentor(username="niravshah", whatsapp_number="+919000000002")
        return make_class(stranger, name="IT-B").id


def _count(app, model):
    with app.app_context():
        return db.session.scalar(select(func.count()).select_from(model))


def _delete(client, class_id, confirmation):
    return client.post(f"/classes/{class_id}/settings/delete", data={"confirmation": confirmation})


def test_settings_page_offers_deletion(signed_in_client, class_id):
    html = signed_in_client.get(f"/classes/{class_id}/settings/").get_data(as_text=True)
    assert "cannot be undone" in html
    assert "Type CE-A exactly as shown" in html
    assert "Delete CE-A</button>" in html


def test_typing_the_name_deletes_the_class_and_everything_in_it(app, signed_in_client, class_id):
    response = _delete(signed_in_client, class_id, " CE-A ")
    assert response.headers["Location"] == "/classes/"
    html = signed_in_client.get("/classes/").get_data(as_text=True)
    assert "Class CE-A deleted, with its semesters and students." in html
    for model in (ClassGroup, Semester, Student):
        assert _count(app, model) == 0


@pytest.mark.parametrize(
    ("typed", "message"),
    [
        ("", "Type the class name to confirm"),
        ("ce-a", "Type CE-A exactly to delete this class"),
        ("CE-B", "Type CE-A exactly to delete this class"),
    ],
)
def test_anything_else_keeps_the_class(app, signed_in_client, class_id, typed, message):
    html = _delete(signed_in_client, class_id, typed).get_data(as_text=True)
    assert "There is a problem" in html
    assert message in html
    assert _count(app, ClassGroup) == 1


def test_another_mentors_class_cannot_be_deleted(app, signed_in_client, strangers_class_id):
    response = _delete(signed_in_client, strangers_class_id, "IT-B")
    assert response.status_code == 404
    with app.app_context():
        assert db.session.get(ClassGroup, strangers_class_id) is not None


def test_deleting_needs_sign_in(app, client, class_id):
    assert _delete(client, class_id, "CE-A").headers["Location"].startswith("/sign-in")
    assert _count(app, ClassGroup) == 1


def test_delete_only_accepts_post(signed_in_client, class_id):
    assert signed_in_client.get(f"/classes/{class_id}/settings/delete").status_code == 405
