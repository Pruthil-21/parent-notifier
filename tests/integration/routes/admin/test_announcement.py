from parent_notifier.core.extensions import db
from parent_notifier.models.activity import ActivityEntry
from tests.factories.accounts import PASSWORD, make_mentor, sign_in

TEXT = "Results meeting on Friday at 3 PM in the seminar hall."


def _publish(client, dismissible="yes", text=TEXT):
    client.post("/admin/users/confirm-password", data={"password": PASSWORD})
    return client.post(
        "/admin/settings/announcement", data={"text": text, "dismissible": dismissible}
    )


def test_a_published_announcement_shows_until_the_mentor_dismisses_it(app, admin_client):
    assert _publish(admin_client).status_code == 302
    admin_client.post("/sign-out")
    with app.app_context():
        make_mentor(username="mentor2", whatsapp_number="+919000000004", password=PASSWORD)
    sign_in(admin_client, username="mentor2")
    page = admin_client.get("/help").get_data(as_text=True)
    assert TEXT in page and "Dismiss announcement" in page
    banner_id = page.split("/announcement/")[1].split("/")[0]
    response = admin_client.post(f"/announcement/{banner_id}/dismiss", data={"next": "//evil.test"})
    assert response.headers["Location"] == "/"
    assert TEXT not in admin_client.get("/help").get_data(as_text=True)


def test_an_always_shown_announcement_cannot_be_dismissed(app, admin_client):
    _publish(admin_client, dismissible="no")
    page = admin_client.get("/help").get_data(as_text=True)
    assert TEXT in page and "Dismiss announcement" not in page
    banner_id = page.split("/announcement/")[1].split("/")[0] if "/announcement/" in page else "1"
    admin_client.post(f"/announcement/{banner_id}/dismiss")
    assert TEXT in admin_client.get("/help").get_data(as_text=True)


def test_publish_replaces_and_remove_takes_it_down(app, admin_client):
    _publish(admin_client)
    _publish(admin_client, text="Second notice")
    page = admin_client.get("/help").get_data(as_text=True)
    assert "Second notice" in page and TEXT not in page
    admin_client.post("/admin/settings/announcement/remove")
    assert "Second notice" not in admin_client.get("/help").get_data(as_text=True)
    with app.app_context():
        events = db.session.scalars(db.select(ActivityEntry.event)).all()
    assert events.count("announcement_published") == 2 and "announcement_removed" in events


def test_announcement_input_is_checked(admin_client):
    assert _publish(admin_client, text="x" * 301).status_code == 400
    assert _publish(admin_client, text="   ").status_code == 400
    assert _publish(admin_client, dismissible="maybe").status_code == 400
