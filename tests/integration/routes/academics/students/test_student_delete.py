import pytest
from sqlalchemy import func, select

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import Result, Student
from parent_notifier.models.activity import ActivityEntry
from parent_notifier.models.messaging import SendLog
from parent_notifier.services.messaging import send_log
from tests.factories.academics import import_sheet, make_class, make_semester
from tests.factories.accounts import make_mentor


@pytest.fixture
def setup(app, mentor):
    """Avi (23CE001) has marks in Sem 4 and one message sent to his parent."""
    with app.app_context():
        class_group = make_class(mentor)
        semester = make_semester(class_group, 4)
        import_sheet(class_group, semester, mentor.id)
        avi = db.session.scalars(select(Student).filter_by(enrollment_no="23CE001")).one()
        send_log.record(
            semester, avi.id, mentor.id, status="sent", language="en", note="", message=""
        )
        return f"/classes/{class_group.id}/sem/4", avi.id


def _count(app, model, **where):
    with app.app_context():
        return db.session.scalar(select(func.count()).select_from(model).filter_by(**where))


def test_edit_page_explains_what_deleting_removes(signed_in_client, setup):
    base, avi = setup
    html = signed_in_client.get(f"{base}/students/{avi}/edit").get_data(as_text=True)
    assert "Delete student" in html
    assert "the record of 1 message sent to their parent" in html
    assert "set the status to Left instead" in html


def test_wrong_confirmation_keeps_the_student(app, signed_in_client, setup):
    base, avi = setup
    response = signed_in_client.post(
        f"{base}/students/{avi}/delete", data={"confirmation": "23CE002"}
    )
    assert "Type 23CE001 exactly to delete this student" in response.get_data(as_text=True)
    assert _count(app, Student, id=avi) == 1


def test_delete_removes_the_student_marks_and_send_record(app, signed_in_client, setup):
    base, avi = setup
    response = signed_in_client.post(
        f"{base}/students/{avi}/delete", data={"confirmation": "23ce001"}
    )
    assert response.headers["Location"] == base
    assert "Avi Shah deleted" in signed_in_client.get(base).get_data(as_text=True)
    assert (_count(app, Student, id=avi), _count(app, Result, student_id=avi)) == (0, 0)
    assert _count(app, SendLog, student_id=avi) == 0
    assert _count(app, Student) == 3
    with app.app_context():
        entry = db.session.scalars(
            db.select(ActivityEntry).filter_by(event="student_deleted")
        ).one()
        assert (entry.category, entry.target_label, entry.class_label) == (
            "data",
            "Avi Shah (23CE001)",
            "CE-A",
        )


def test_another_mentors_student_cannot_be_deleted(app, client, setup):
    base, avi = setup
    with app.app_context():
        make_mentor(
            username="niravshah", whatsapp_number="+919000000002", password="Winter-lecture-42"
        )
    client.post("/sign-in", data={"username": "niravshah", "password": "Winter-lecture-42"})
    response = client.post(f"{base}/students/{avi}/delete", data={"confirmation": "23CE001"})
    assert response.status_code == 404
    assert _count(app, Student, id=avi) == 1
