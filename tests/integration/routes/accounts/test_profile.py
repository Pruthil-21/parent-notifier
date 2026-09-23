import pytest
from werkzeug.security import check_password_hash

from parent_notifier.core.extensions import db
from parent_notifier.models.accounts import Mentor
from parent_notifier.routes.accounts.throttling import FAILURES_PER_USERNAME
from tests.factories.accounts import PASSWORD, make_mentor, sign_in

DETAILS = {"full_name": "Asha R. Patel", "username": "ashap", "whatsapp_number": "90000 00009"}
NEW_PASSWORD = "Brand-new-pass-1"


def _saved(app, mentor_id):
    with app.app_context():
        return db.session.get(Mentor, mentor_id)


def _change_password(client, current=PASSWORD, new=NEW_PASSWORD):
    return client.post("/profile/password", data={"current_password": current, "new_password": new})


def test_profile_needs_sign_in(client):
    for method, path in (("get", "/profile/"), ("post", "/profile/account")):
        assert getattr(client, method)(path).headers["Location"].startswith("/sign-in")


def test_page_shows_current_details_and_is_in_the_navigation(signed_in_client):
    html = signed_in_client.get("/profile/").get_data(as_text=True)
    assert 'value="Asha Patel"' in html
    assert 'value="+91 90000 00001"' in html
    assert '<a class="account-menu__item" href="/profile/">' in html
    assert 'aria-current="page"' in html
    assert html.count('name="csrf_token"') == 6
    assert 'id="csrf_token"' not in html


def test_saving_details_updates_the_account(app, signed_in_client, mentor):
    response = signed_in_client.post("/profile/account", data=DETAILS, follow_redirects=True)
    html = response.get_data(as_text=True)
    assert "Account details saved." in html
    assert 'Sending as <span class="numeric">+91 90000 00009</span>' in html
    saved = _saved(app, mentor.id)
    assert (saved.full_name, saved.username, saved.whatsapp_number) == (
        "Asha R. Patel",
        "ashap",
        "+919000000009",
    )
    assert signed_in_client.get("/profile/").status_code == 200


def test_keeping_your_own_username_is_allowed(signed_in_client):
    data = DETAILS | {"username": "AshaPatel"}
    assert signed_in_client.post("/profile/account", data=data).status_code == 302


def test_another_mentors_username_is_refused(app, signed_in_client, mentor):
    with app.app_context():
        make_mentor(username="niravshah", whatsapp_number="+919000000002")
    html = signed_in_client.post(
        "/profile/account", data=DETAILS | {"username": "NiravShah"}
    ).get_data(as_text=True)
    assert "That username is taken. Choose another" in html
    assert _saved(app, mentor.id).username == "ashapatel"


def test_invalid_details_are_explained_and_not_saved(app, signed_in_client, mentor):
    data = {"full_name": "Prof. Asha", "username": "a", "whatsapp_number": "123"}
    html = signed_in_client.post("/profile/account", data=data).get_data(as_text=True)
    assert "There is a problem" in html
    assert "Enter a 10-digit mobile number" in html
    assert _saved(app, mentor.id).full_name == "Asha Patel"


def test_extra_fields_cannot_change_other_columns(app, signed_in_client, mentor):
    data = DETAILS | {"session_version": "99", "password_hash": "x", "id": "7"}
    signed_in_client.post("/profile/account", data=data)
    saved = _saved(app, mentor.id)
    assert saved.session_version == 1
    assert saved.password_hash.startswith("scrypt:")


def test_changing_password_keeps_this_browser_and_signs_out_others(app, client, mentor):
    other_browser = app.test_client()
    sign_in(other_browser)
    sign_in(client)
    response = _change_password(client)
    assert response.headers["Location"] == "/profile/"
    assert "Other browsers have been signed out." in client.get("/profile/").get_data(as_text=True)
    assert other_browser.get("/").status_code == 302
    assert check_password_hash(_saved(app, mentor.id).password_hash, NEW_PASSWORD)


def test_remembered_browser_stays_remembered_after_a_change(client, mentor):
    sign_in(client, remember="y")
    old_cookie = client.get_cookie("remember_token").value
    _change_password(client)
    assert client.get_cookie("remember_token").value != old_cookie


def test_wrong_current_password_changes_nothing(app, signed_in_client, mentor):
    html = _change_password(signed_in_client, current="not-it").get_data(as_text=True)
    assert "Your current password is incorrect" in html
    assert 'href="#current_password"' in html
    assert check_password_hash(_saved(app, mentor.id).password_hash, PASSWORD)


@pytest.mark.parametrize("new", ["", "short", "x" * 129])
def test_new_password_must_be_8_to_128_characters(signed_in_client, new):
    html = _change_password(signed_in_client, new=new).get_data(as_text=True)
    assert "New password" in html
    assert "There is a problem" in html


def test_guessing_the_current_password_hits_the_sign_in_lockout(client, mentor):
    sign_in(client)
    for _ in range(FAILURES_PER_USERNAME):
        _change_password(client, current="not-it")
    response = _change_password(client)
    assert response.status_code == 429
    assert "Too many password attempts." in response.get_data(as_text=True)
    client.post("/sign-out")
    assert sign_in(client).status_code == 429
