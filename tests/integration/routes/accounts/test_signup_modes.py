from sqlalchemy import select

from parent_notifier.core.extensions import db
from parent_notifier.models.accounts import Mentor
from parent_notifier.services.accounts import registration
from tests.factories.accounts import PASSWORD

REQUEST = {
    "full_name": "Nirav Shah",
    "username": "niravshah",
    "whatsapp_number": "90000 00002",
    "department": "Civil Engineering",
    "password": PASSWORD,
}


def _mode(app, mode):
    with app.app_context():
        registration.set_signup_mode(mode)


def _saved(app):
    with app.app_context():
        return db.session.scalar(select(Mentor).where(Mentor.username == "niravshah"))


def test_sign_up_is_off_until_the_admin_opens_it(app, client):
    assert "Ask the admin to create your account" in client.get("/sign-in").get_data(as_text=True)
    page = client.get("/create-account").get_data(as_text=True)
    assert "Accounts are created by the admin" in page and "<form" not in page
    assert client.post("/create-account", data=REQUEST).status_code == 403
    assert _saved(app) is None


def test_a_request_waits_for_approval_then_gets_its_code_at_first_sign_in(app, client):
    _mode(app, registration.SIGNUP_APPROVAL)
    assert "Request an account" in client.get("/sign-in").get_data(as_text=True)
    sent = client.post("/create-account", data=REQUEST).get_data(as_text=True)
    assert "Request sent" in sent and "niravshah" in sent
    mentor = _saved(app)
    assert (mentor.approved, mentor.recovery_code_hash) == (False, "")
    signing_in = {"username": "niravshah", "password": PASSWORD}
    refused = client.post("/sign-in", data=signing_in).get_data(as_text=True)
    assert "waiting for the admin&#39;s approval" in refused
    assert client.get("/").status_code == 302  # still signed out

    with app.app_context():
        db.session.get(Mentor, mentor.id).approved = True
        db.session.commit()
    response = client.post("/sign-in", data=signing_in)
    assert response.headers["Location"] == "/recovery-code"
    assert _saved(app).recovery_code_hash and _saved(app).last_sign_in_at


def test_a_wrong_password_on_a_waiting_account_says_nothing_about_it(app, client):
    _mode(app, registration.SIGNUP_APPROVAL)
    client.post("/create-account", data=REQUEST)
    html = client.post("/sign-in", data={"username": "niravshah", "password": "wrong-password"})
    text = html.get_data(as_text=True)
    assert "Username or password is incorrect." in text and "approval" not in text
