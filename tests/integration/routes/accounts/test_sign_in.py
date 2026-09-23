import pytest

from parent_notifier.core.extensions import db
from parent_notifier.models.accounts import Mentor
from tests.factories.accounts import PASSWORD, sign_in

INCORRECT = "Username or password is incorrect."


def test_page_has_fields_password_managers_can_fill(client):
    html = client.get("/sign-in").get_data(as_text=True)
    assert 'autocomplete="username"' in html
    assert 'autocomplete="current-password"' in html
    assert 'type="password"' in html
    assert "novalidate" in html
    assert 'name="remember"' in html
    assert "checked" not in html


def test_correct_details_sign_in_and_go_home(client, mentor):
    response = sign_in(client)
    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    assert "Signed in as Asha Patel" in client.get("/").get_data(as_text=True)


@pytest.mark.parametrize(
    ("username", "password"),
    [("ashapatel", "wrong-password"), ("nobody", PASSWORD), ("ashapatel", PASSWORD + " ")],
    ids=["wrong password", "unknown username", "password with extra space"],
)
def test_any_wrong_combination_gets_the_same_message(client, mentor, username, password):
    response = sign_in(client, username, password)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert INCORRECT in html
    assert 'href="#username"' in html
    assert client.get("/").status_code == 302


def test_username_is_kept_but_password_is_not(client, mentor):
    html = sign_in(client, "ashapatel", "wrong-password").get_data(as_text=True)
    assert 'value="ashapatel"' in html
    assert "wrong-password" not in html


def test_empty_fields_say_what_to_enter(client):
    html = sign_in(client, "", "").get_data(as_text=True)
    assert "Enter your username" in html
    assert "Enter your password" in html
    assert 'aria-invalid="true"' in html
    assert 'aria-describedby="username-error"' in html
    assert INCORRECT not in html


def test_signed_in_mentor_skips_the_sign_in_page(signed_in_client):
    response = signed_in_client.get("/sign-in")
    assert response.headers["Location"] == "/"


def test_pages_that_need_sign_in_send_mentors_here_and_back(client, mentor):
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"] == "/sign-in?next=%2F"
    html = client.get(response.headers["Location"]).get_data(as_text=True)
    assert 'name="next" type="hidden" value="/"' in html


def test_next_path_on_this_site_is_followed(client, mentor):
    response = sign_in(client, next="/?tab=classes")
    assert response.headers["Location"] == "/?tab=classes"


@pytest.mark.parametrize(
    "target",
    [
        "https://evil.example/",
        "//evil.example/",
        "/\\evil.example",
        "\\\\evil.example",
        "/\t/evil.example",
        "javascript:alert(1)",
        "evil.example",
        "",
    ],
)
def test_next_never_leaves_the_site(client, mentor, target):
    response = sign_in(client, next=target)
    assert response.headers["Location"] == "/"


def test_session_cookie_is_replaced_on_sign_in(client, mentor):
    client.get("/sign-in")
    with client.session_transaction() as session:
        session["planted"] = "value from before sign-in"
    sign_in(client)
    with client.session_transaction() as session:
        assert "planted" not in session


def test_without_stay_signed_in_there_is_no_remember_cookie(client, mentor):
    sign_in(client)
    assert client.get_cookie("remember_token") is None


def test_stay_signed_in_sets_a_protected_remember_cookie(client, mentor):
    response = sign_in(client, remember="y")
    header = next(h for h in response.headers.getlist("Set-Cookie") if "remember_token" in h)
    assert "HttpOnly" in header
    assert "SameSite=Lax" in header
    assert "Expires=" in header


def test_raising_the_session_version_signs_the_mentor_out(app, client, mentor):
    sign_in(client, remember="y")
    with app.app_context():
        db.session.get(Mentor, mentor.id).session_version += 1
        db.session.commit()
    assert client.get("/").status_code == 302
