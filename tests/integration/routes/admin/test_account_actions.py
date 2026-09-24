import re
from datetime import timedelta

from parent_notifier.core.extensions import db
from parent_notifier.models.accounts import Mentor
from parent_notifier.models.activity import ActivityEntry
from parent_notifier.services.shared import clock
from tests.factories.accounts import PASSWORD, sign_in

NEW = {
    "full_name": "Nirav Shah",
    "username": "niravshah",
    "whatsapp_number": "90000 00002",
    "department": "civil engineering",
}


def _confirm(client):
    return client.post("/admin/users/confirm-password", data={"password": PASSWORD})


def _one_time_password(html: str) -> str:
    return re.search(r'one-time-password__value">([^<]+)<', html).group(1)


def test_creating_an_account_needs_a_confirmed_password_then_shows_it_once(app, admin_client):
    first = admin_client.post("/admin/users/new", data=NEW)
    assert first.headers["Location"].startswith("/admin/users/confirm-password")
    wrong = admin_client.post("/admin/users/confirm-password", data={"password": "nope-nope"})
    assert "Your password is incorrect" in wrong.get_data(as_text=True)
    assert _confirm(admin_client).status_code == 302

    html = admin_client.post("/admin/users/new", data=NEW).get_data(as_text=True)
    password = _one_time_password(html)
    with app.app_context():
        account = db.session.scalars(db.select(Mentor).filter_by(username="niravshah")).one()
        assert (account.department, account.must_change_password, account.role) == (
            "Civil Engineering",
            True,
            "mentor",
        )
        entries = db.session.scalars(db.select(ActivityEntry).filter_by(category="admin")).all()
        assert [e.event for e in entries] == ["account_created"]
        assert password not in str([vars(e) for e in entries])


def test_reset_and_sign_out_everywhere_act_on_the_account(app, admin_client, mentor):
    _confirm(admin_client)
    html = admin_client.post(f"/admin/users/{mentor.id}/reset-password").get_data(as_text=True)
    password = _one_time_password(html)
    with app.app_context():
        version = db.session.get(Mentor, mentor.id).session_version
    admin_client.post(f"/admin/users/{mentor.id}/sign-out")
    with app.app_context():
        assert db.session.get(Mentor, mentor.id).session_version == version + 1
    assert password and "Every browser Asha Patel was signed in on has been signed out." in html


def test_the_old_password_stops_working_after_a_reset(app, client, admin, mentor):
    sign_in(client, username="pruthil")
    _confirm(client)
    client.post(f"/admin/users/{mentor.id}/reset-password")
    client.post("/sign-out")
    response = client.post("/sign-in", data={"username": "ashapatel", "password": PASSWORD})
    assert "Username or password is incorrect." in response.get_data(as_text=True)


def test_the_admin_cannot_act_on_their_own_account_here(admin_client, admin):
    _confirm(admin_client)
    for action in ("reset-password", "sign-out"):
        assert admin_client.post(f"/admin/users/{admin}/{action}").status_code == 404
    assert admin_client.get(f"/admin/users/{admin}/edit").status_code == 404


def test_a_confirmation_lasts_fifteen_minutes(app, admin_client, mentor, monkeypatch):
    _confirm(admin_client)
    later = clock.now() + timedelta(minutes=16)
    monkeypatch.setattr(clock, "now", lambda: later)
    response = admin_client.post(f"/admin/users/{mentor.id}/sign-out")
    assert response.headers["Location"].startswith("/admin/users/confirm-password")


def test_the_admin_edits_an_accounts_details(app, admin_client, mentor):
    data = NEW | {"username": "ashap", "full_name": "Asha R. Patel"}
    response = admin_client.post(f"/admin/users/{mentor.id}/edit", data=data)
    assert response.headers["Location"] == f"/admin/users/{mentor.id}"
    with app.app_context():
        saved = db.session.get(Mentor, mentor.id)
        assert (saved.full_name, saved.username, saved.department) == (
            "Asha R. Patel",
            "ashap",
            "Civil Engineering",
        )
