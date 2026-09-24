import pytest
from sqlalchemy import select

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup, Student
from parent_notifier.models.accounts import Mentor
from parent_notifier.models.activity import ActivityEntry
from parent_notifier.models.messaging import SendLog
from parent_notifier.services.messaging import send_log
from tests.factories.academics import import_sheet, make_class, make_semester
from tests.factories.accounts import PASSWORD, make_mentor, sign_in


@pytest.fixture
def setup(app, mentor):
    """Asha's CE-A has a sheet and one sent message; Nirav has a class of his own."""
    with app.app_context():
        class_group = make_class(mentor)
        semester = make_semester(class_group, 4)
        import_sheet(class_group, semester, mentor.id)
        student = db.session.scalars(select(Student)).first()
        send_log.record(
            semester, student.id, mentor.id, status="sent", language="en", note="", message=""
        )
        nirav = make_mentor(
            full_name="Nirav Shah",
            username="niravshah",
            whatsapp_number="+919000000002",
            password=PASSWORD,
        )
        make_class(nirav, name="CE-B")
        return class_group.id, nirav.id


def _confirmed(client):
    client.post("/admin/users/confirm-password", data={"password": PASSWORD})
    return client


def test_moving_a_class_gives_it_to_the_new_mentor_with_its_history(
    app, client, admin, mentor, setup
):
    class_id, nirav = setup
    sign_in(client, username="pruthil")
    _confirmed(client)
    data = {"classes": [class_id], "to_mentor": nirav}
    response = client.post(f"/admin/users/{mentor.id}/transfer", data=data)
    assert response.headers["Location"] == f"/admin/users/{mentor.id}"
    with app.app_context():
        assert db.session.get(ClassGroup, class_id).mentor_id == nirav
        assert db.session.scalars(select(SendLog.mentor_id)).one() == mentor.id  # who sent it
    client.post("/sign-out")
    sign_in(client, username="niravshah")
    assert client.get(f"/classes/{class_id}/sem/4").status_code == 200
    client.post("/sign-out")
    sign_in(client)
    assert client.get(f"/classes/{class_id}/sem/4").status_code == 404


def test_a_class_name_the_new_mentor_already_has_stops_the_move(app, admin_client, mentor, setup):
    class_id, nirav = setup
    with app.app_context():
        db.session.get(ClassGroup, class_id).name = "CE-B"
        db.session.commit()
    _confirmed(admin_client)
    html = admin_client.post(
        f"/admin/users/{mentor.id}/transfer", data={"classes": [class_id], "to_mentor": nirav}
    ).get_data(as_text=True)
    assert "Nirav Shah already has a class called CE-B. Rename it first." in html
    with app.app_context():
        assert db.session.get(ClassGroup, class_id).mentor_id == mentor.id


def test_an_account_is_deleted_only_once_its_classes_are_gone(app, admin_client, mentor, setup):
    class_id, nirav = setup
    _confirmed(admin_client)
    page = admin_client.get(f"/admin/users/{mentor.id}").get_data(as_text=True)
    assert "Move them to another mentor first" in page
    refused = admin_client.post(
        f"/admin/users/{mentor.id}/delete", data={"confirmation": "ashapatel"}
    )
    assert refused.status_code == 400

    admin_client.post(
        f"/admin/users/{mentor.id}/transfer", data={"classes": [class_id], "to_mentor": nirav}
    )
    wrong = admin_client.post(f"/admin/users/{mentor.id}/delete", data={"confirmation": "asha"})
    assert "Type ashapatel exactly to delete this account" in wrong.get_data(as_text=True)
    done = admin_client.post(f"/admin/users/{mentor.id}/delete", data={"confirmation": "AshaPatel"})
    assert done.headers["Location"] == "/admin/users/"
    with app.app_context():
        assert db.session.get(Mentor, mentor.id) is None
        assert db.session.scalars(select(SendLog.mentor_id)).one() is None  # the record stays
        deleted = db.session.scalars(select(ActivityEntry).filter_by(event="account_deleted")).one()
        assert deleted.target_label == "Asha Patel (ashapatel)"
