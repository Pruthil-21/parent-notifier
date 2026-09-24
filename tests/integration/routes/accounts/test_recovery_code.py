import re

import pytest
from sqlalchemy import select
from werkzeug.security import check_password_hash

from parent_notifier.core.extensions import db
from parent_notifier.models.accounts import Mentor

pytestmark = pytest.mark.usefixtures("open_signup")


ACCOUNT = {
    "full_name": "Nirav Shah",
    "username": "niravshah",
    "whatsapp_number": "9000000002",
    "department": "Civil Engineering",
    "password": "Monsoon-exams-7",
}
CODE = re.compile(r"data-recovery-code>([A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4})<")


def _register(client):
    response = client.post("/create-account", data=ACCOUNT)
    assert response.headers["Location"] == "/recovery-code"
    return client.get("/recovery-code").get_data(as_text=True)


def test_new_account_is_shown_its_code_once_in_groups(app, client):
    html = _register(client)
    shown = CODE.search(html).group(1)
    with app.app_context():
        mentor = db.session.scalar(select(Mentor).where(Mentor.username == "niravshah"))
        assert check_password_hash(mentor.recovery_code_hash, shown.replace("-", ""))
    assert "Your account is ready." in html
    assert "only way to reset" in html


def test_copy_button_waits_for_javascript_but_download_does_not(client):
    html = _register(client)
    assert re.search(r"<button[^>]*data-copy-target=\"recovery-code\"[^>]*hidden", html)
    assert 'href="/recovery-code.txt"' in html


def test_download_is_a_text_attachment_with_the_code(client):
    shown = CODE.search(_register(client)).group(1)
    response = client.get("/recovery-code.txt")
    assert response.status_code == 200
    assert response.mimetype == "text/plain"
    assert response.headers["Content-Disposition"].startswith("attachment;")
    assert response.headers["Cache-Control"] == "no-store"
    assert shown in response.get_data(as_text=True)


def test_continue_needs_the_box_ticked(client):
    _register(client)
    response = client.post("/recovery-code", data={})
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Tick the box to confirm you have saved the code" in html
    assert CODE.search(html)


def test_after_continue_the_code_is_gone(client):
    _register(client)
    response = client.post("/recovery-code", data={"saved": "y"})
    assert response.headers["Location"] == "/"
    with client.session_transaction() as session:
        assert not any("recovery" in key for key in session)
    assert client.get("/recovery-code").headers["Location"] == "/"
    assert client.get("/recovery-code.txt").status_code == 404


def test_code_page_needs_sign_in(client):
    assert client.get("/recovery-code").headers["Location"].startswith("/sign-in")
    assert client.get("/recovery-code.txt").headers["Location"].startswith("/sign-in")


def test_signed_in_mentor_without_a_new_code_is_sent_home(signed_in_client):
    assert signed_in_client.get("/recovery-code").headers["Location"] == "/"


def test_continue_target_in_the_session_cannot_point_elsewhere(client):
    _register(client)
    with client.session_transaction() as session:
        session["after_recovery_code"] = "https://evil.example/"
    response = client.post("/recovery-code", data={"saved": "y"})
    assert response.headers["Location"] == "/"
