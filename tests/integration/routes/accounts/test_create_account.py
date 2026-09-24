import pytest
from sqlalchemy import select

from parent_notifier.core.extensions import db
from parent_notifier.models.accounts import Mentor
from parent_notifier.services.accounts import registration

VALID = {
    "full_name": "  Nirav   Shah ",
    "username": "NiravShah",
    "whatsapp_number": "+91 90000 00002",
    "department": "Civil Engineering",
    "password": "Monsoon-exams-7",
}


def _mentor(app, username="niravshah"):
    with app.app_context():
        return db.session.scalar(select(Mentor).where(Mentor.username == username))


def test_page_has_hints_and_the_right_autocomplete(client):
    html = client.get("/create-account").get_data(as_text=True)
    assert "As it should appear in messages, without Prof." in html
    assert "10-digit mobile number, like 98765 43210" in html
    assert 'autocomplete="new-password"' in html
    assert 'type="tel"' in html
    assert "confirm" not in html.lower()
    assert 'href="/sign-in"' in html


def test_sign_in_page_links_here(client):
    assert 'href="/create-account"' in client.get("/sign-in").get_data(as_text=True)


def test_new_account_is_saved_and_signed_in(app, client):
    response = client.post("/create-account", data=VALID)
    assert response.status_code == 302
    mentor = _mentor(app)
    assert mentor.full_name == "Nirav Shah"
    assert mentor.whatsapp_number == "+919000000002"
    assert mentor.password_hash.startswith("scrypt:")
    assert 'aria-label="Account: Nirav Shah"' in client.get("/").get_data(as_text=True)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("full_name", "", "Enter your full name"),
        ("full_name", "Prof. Nirav Shah", "Enter your name without Prof."),
        ("full_name", "professor nirav", "Enter your name without Prof."),
        ("full_name", "Nirav\u0000Shah", "Full name can only use letters"),
        ("full_name", "N" * 81, "Full name must be 80 characters or fewer"),
        ("username", "", "Enter a username"),
        ("username", "ns", "Username must be 3 to 30 characters"),
        ("username", "nirav shah", "Username can only use letters"),
        ("username", ".nirav", "Username can only use letters"),
        ("whatsapp_number", "", "Enter your WhatsApp number"),
        ("whatsapp_number", "12345", "Enter a 10-digit mobile number, like 98765 43210"),
        ("password", "", "Enter a password"),
        ("password", "short", "Password must be 8 to 128 characters"),
        ("password", "x" * 129, "Password must be 8 to 128 characters"),
    ],
)
def test_each_problem_is_explained_and_nothing_is_saved(app, client, field, value, message):
    response = client.post("/create-account", data=VALID | {field: value})
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "There is a problem" in html
    assert message in html
    assert f'href="#{field}"' in html
    assert _mentor(app) is None


def test_every_problem_shows_at_once(client):
    html = client.post("/create-account", data={}).get_data(as_text=True)
    for message in ("Enter your full name", "Enter a username", "Enter your WhatsApp number"):
        assert message in html


def test_taken_username_is_refused_whatever_the_case(client, mentor):
    html = client.post("/create-account", data=VALID | {"username": "AshaPatel"}).get_data(
        as_text=True
    )
    assert "That username is taken. Choose another" in html


def test_typed_values_come_back_except_the_password(client):
    html = client.post("/create-account", data=VALID | {"username": ""}).get_data(as_text=True)
    assert 'value="+91 90000 00002"' in html
    assert "Monsoon-exams-7" not in html


def test_extra_fields_in_the_request_are_ignored(app, client):
    client.post("/create-account", data=VALID | {"session_version": "99", "id": "42"})
    mentor = _mentor(app)
    assert mentor.session_version == 1
    assert mentor.id != 42


def test_signed_in_mentor_is_sent_home(signed_in_client):
    assert signed_in_client.get("/create-account").headers["Location"] == "/"


def test_one_computer_can_create_only_ten_accounts_an_hour(client):
    for number in range(10):
        data = VALID | {"username": f"mentor{number}"}
        assert client.post("/create-account", data=data).status_code == 302
        client.post("/sign-out")
    response = client.post("/create-account", data=VALID)
    assert response.status_code == 429
    assert "Too many accounts were created from this computer." in response.get_data(as_text=True)


def test_username_taken_between_check_and_save_is_still_refused(client, mentor, monkeypatch):
    monkeypatch.setattr(registration, "username_taken", lambda _username: False)
    response = client.post("/create-account", data=VALID | {"username": "ashapatel"})
    assert response.status_code == 200
    assert "That username is taken. Choose another" in response.get_data(as_text=True)
