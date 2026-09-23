import re

import pytest

from parent_notifier.core.extensions import db
from parent_notifier.models.accounts import Mentor
from parent_notifier.routes.accounts.throttling import FAILURES_PER_USERNAME
from parent_notifier.services.accounts import recovery_codes
from tests.factories.accounts import PASSWORD, sign_in

CODE = "ABCDEFGHJKMN"
NEW_PASSWORD = "Brand-new-pass-1"
INCORRECT = "Username or recovery code is incorrect."


@pytest.fixture
def mentor_with_code(app, mentor):
    with app.app_context():
        db.session.get(Mentor, mentor.id).recovery_code_hash = recovery_codes.hash_code(CODE)
        db.session.commit()
    return mentor


def _reset(client, username="ashapatel", code=CODE, password=NEW_PASSWORD):
    data = {"username": username, "recovery_code": code, "new_password": password}
    return client.post("/reset-password", data=data)


def test_sign_in_page_links_here(client):
    assert 'href="/reset-password"' in client.get("/sign-in").get_data(as_text=True)


def test_page_has_the_three_fields(client):
    html = client.get("/reset-password").get_data(as_text=True)
    assert 'name="recovery_code"' in html
    assert 'autocomplete="new-password"' in html
    assert 'href="/sign-in"' in html


def test_right_code_resets_signs_in_and_shows_a_new_code(client, mentor_with_code):
    response = _reset(client, code="abcd-efgh-jkmn")
    assert response.headers["Location"] == "/recovery-code"
    html = client.get("/recovery-code").get_data(as_text=True)
    new_code = re.search(r"data-recovery-code>([A-Z0-9-]{14})<", html).group(1)
    assert new_code.replace("-", "") != CODE
    assert "Your password has been reset." in html
    client.post("/sign-out")
    assert sign_in(client, password=PASSWORD).status_code == 200
    assert sign_in(client, password=NEW_PASSWORD).status_code == 302


def test_old_code_stops_working(client, mentor_with_code):
    _reset(client)
    client.post("/sign-out")
    assert INCORRECT in _reset(client, password="Third-pass-333").get_data(as_text=True)


def test_reset_signs_out_every_other_browser(app, mentor_with_code):
    other_browser = app.test_client()
    sign_in(other_browser, remember="y")
    assert other_browser.get("/").status_code == 200
    _reset(app.test_client())
    assert other_browser.get("/").status_code == 302


@pytest.mark.parametrize(
    ("username", "code"),
    [("ashapatel", "ABCDEFGHJKMP"), ("nobody", CODE), ("ashapatel", "ABCD")],
    ids=["wrong code", "unknown username", "too short"],
)
def test_any_wrong_combination_gets_one_message(client, mentor_with_code, username, code):
    response = _reset(client, username, code)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert INCORRECT in html
    assert sign_in(client).status_code == 302


def test_new_password_is_checked_before_the_code(client, mentor_with_code):
    html = _reset(client, code="WRONGWRONGWR", password="short").get_data(as_text=True)
    assert "New password must be 8 to 128 characters" in html
    assert INCORRECT not in html


def test_reset_shares_the_sign_in_lockout(client, mentor_with_code):
    for _ in range(FAILURES_PER_USERNAME - 2):
        sign_in(client, password="wrong-password")
    _reset(client, code="WRONGWRONGWR")
    _reset(client, code="WRONGWRONGWR")
    response = _reset(client)
    assert response.status_code == 429
    assert "Too many password reset attempts." in response.get_data(as_text=True)
    assert sign_in(client).status_code == 429


def test_signed_in_mentor_is_sent_home(signed_in_client):
    assert signed_in_client.get("/reset-password").headers["Location"] == "/"
