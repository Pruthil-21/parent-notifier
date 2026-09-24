import re

from parent_notifier.core.extensions import db
from parent_notifier.models.accounts import Mentor
from parent_notifier.services.accounts import registration
from tests.factories.accounts import PASSWORD, make_mentor


def _confirm(client):
    client.post("/admin/users/confirm-password", data={"password": PASSWORD})


def test_the_admin_chooses_who_can_create_an_account(app, admin_client, client):
    page = admin_client.get("/admin/settings/").get_data(as_text=True)
    assert re.search(r'<input checked[^>]*value="off"', page)  # off until the admin changes it
    assert (
        admin_client.post("/admin/settings/", data={"mode": "open"})
        .headers["Location"]
        .startswith("/admin/users/confirm-password")
    )
    _confirm(admin_client)
    admin_client.post("/admin/settings/", data={"mode": "approval"})
    with app.app_context():
        assert registration.signup_mode() == "approval"
    assert admin_client.post("/admin/settings/", data={"mode": "anything"}).status_code == 400


def test_requests_are_approved_or_rejected(app, admin_client):
    with app.app_context():
        waiting = make_mentor(
            full_name="Nirav Shah",
            username="niravshah",
            whatsapp_number="+919000000002",
            approved=False,
        )
        other = make_mentor(
            full_name="Kiran Rao",
            username="kiranrao",
            whatsapp_number="+919000000003",
            approved=False,
        )
        ids = waiting.id, other.id
    page = admin_client.get("/admin/users/").get_data(as_text=True)
    assert "Account requests" in page and "Nirav Shah" in page and "Kiran Rao" in page
    _confirm(admin_client)
    admin_client.post(f"/admin/users/{ids[0]}/approve")
    admin_client.post(f"/admin/users/{ids[1]}/reject")
    with app.app_context():
        assert db.session.get(Mentor, ids[0]).approved is True
        assert db.session.get(Mentor, ids[1]) is None
    assert admin_client.post(f"/admin/users/{ids[0]}/reject").status_code == 404  # approved now
    assert "Account requests" not in admin_client.get("/admin/users/").get_data(as_text=True)
