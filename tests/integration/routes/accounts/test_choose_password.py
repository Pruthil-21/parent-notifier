from parent_notifier.core.extensions import db
from parent_notifier.models.accounts import Mentor
from parent_notifier.services.accounts import registration
from tests.factories.accounts import make_mentor


def _temporary(app):
    with app.app_context():
        mentor = make_mentor(password="Winter-lecture-42")
        return mentor.id, registration.set_temporary_password(mentor)


def test_an_admin_set_password_opens_only_the_page_to_choose_your_own(app, client):
    mentor_id, temporary = _temporary(app)
    assert len(temporary) == 14 and temporary.count("-") == 2
    old = client.post("/sign-in", data={"username": "ashapatel", "password": "Winter-lecture-42"})
    assert "Username or password is incorrect." in old.get_data(as_text=True)

    response = client.post("/sign-in", data={"username": "ashapatel", "password": temporary})
    assert response.headers["Location"] == "/choose-password"
    assert client.get("/classes/").headers["Location"] == "/choose-password"
    short = client.post("/choose-password", data={"new_password": "short"})
    assert "New password must be 8 to 128 characters" in short.get_data(as_text=True)

    chosen = client.post("/choose-password", data={"new_password": "Summer-lecture-43"})
    assert chosen.headers["Location"] == "/recovery-code"
    with app.app_context():
        mentor = db.session.get(Mentor, mentor_id)
        assert mentor.must_change_password is False and mentor.recovery_code_hash
    assert client.get("/choose-password").headers["Location"] == "/"
