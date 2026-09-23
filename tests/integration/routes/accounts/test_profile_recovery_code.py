import re

from werkzeug.security import check_password_hash

from parent_notifier.core.extensions import db
from parent_notifier.models.accounts import Mentor
from parent_notifier.routes.accounts.throttling import FAILURES_PER_USERNAME
from parent_notifier.services.accounts import recovery_codes
from tests.factories.accounts import PASSWORD

OLD_CODE = "ABCDEFGHJKMN"


def _regenerate(client, password=PASSWORD):
    return client.post("/profile/recovery-code", data={"password": password})


def _stored_hash(app, mentor_id):
    with app.app_context():
        return db.session.get(Mentor, mentor_id).recovery_code_hash


def test_section_asks_for_the_current_password(signed_in_client):
    html = signed_in_client.get("/profile/").get_data(as_text=True)
    assert "Create new recovery code" in html
    assert 'id="password"' in html
    assert html.count('id="current_password"') == 1


def test_new_code_is_shown_once_and_continue_returns_to_profile(app, signed_in_client, mentor):
    with app.app_context():
        db.session.get(Mentor, mentor.id).recovery_code_hash = recovery_codes.hash_code(OLD_CODE)
        db.session.commit()
    response = _regenerate(signed_in_client)
    assert response.headers["Location"] == "/recovery-code"
    html = signed_in_client.get("/recovery-code").get_data(as_text=True)
    assert "Your old one no longer works." in html
    shown = re.search(r"data-recovery-code>([A-Z0-9-]{14})<", html).group(1)
    stored = _stored_hash(app, mentor.id)
    assert check_password_hash(stored, shown.replace("-", ""))
    assert not check_password_hash(stored, OLD_CODE)
    done = signed_in_client.post("/recovery-code", data={"saved": "y"})
    assert done.headers["Location"] == "/profile/"


def test_regenerating_keeps_the_mentor_signed_in(signed_in_client):
    _regenerate(signed_in_client)
    assert signed_in_client.get("/profile/").status_code == 200


def test_wrong_password_keeps_the_old_code(app, signed_in_client, mentor):
    before = _stored_hash(app, mentor.id)
    html = _regenerate(signed_in_client, "not-it").get_data(as_text=True)
    assert "Your current password is incorrect" in html
    assert 'href="#password"' in html
    assert _stored_hash(app, mentor.id) == before


def test_needs_sign_in(client):
    assert _regenerate(client).headers["Location"].startswith("/sign-in")


def test_guesses_share_the_sign_in_lockout(signed_in_client):
    for _ in range(FAILURES_PER_USERNAME):
        _regenerate(signed_in_client, "not-it")
    response = _regenerate(signed_in_client)
    assert response.status_code == 429
    html = response.get_data(as_text=True)
    assert "Too many password attempts." in html
    assert html.index("Too many password attempts.") > html.index('id="recovery-heading"')
