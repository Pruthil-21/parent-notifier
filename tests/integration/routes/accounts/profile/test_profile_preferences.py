import pytest

from parent_notifier.core.extensions import db
from parent_notifier.models.accounts import Mentor

SAFETY = {
    "send_gap_seconds": "30",
    "burst_size": "10",
    "burst_pause_minutes": "8",
    "daily_send_limit": "40",
}


def _saved(app, mentor_id):
    with app.app_context():
        return db.session.get(Mentor, mentor_id)


def test_sections_show_current_settings(signed_in_client):
    html = signed_in_client.get("/profile/").get_data(as_text=True)
    assert '<option selected value="en">English</option>' in html
    assert '<option selected value="system">System</option>' in html
    for value in ("20", "15", "5", "60"):
        assert f'value="{value}"' in html


def test_theme_and_default_language_are_saved(app, signed_in_client, mentor):
    data = {"theme": "dark", "message_language": "gu"}
    response = signed_in_client.post("/profile/preferences", data=data)
    assert response.headers["Location"] == "/profile/"
    saved = _saved(app, mentor.id)
    assert (saved.theme, saved.message_language) == ("dark", "gu")


def test_unknown_language_is_refused(app, signed_in_client, mentor):
    html = signed_in_client.post(
        "/profile/preferences", data={"theme": "system", "message_language": "hi"}
    )
    assert "There is a problem" in html.get_data(as_text=True)
    assert _saved(app, mentor.id).message_language == "en"


def test_sending_safety_is_saved(app, signed_in_client, mentor):
    response = signed_in_client.post("/profile/sending-safety", data=SAFETY, follow_redirects=True)
    assert "Sending safety saved." in response.get_data(as_text=True)
    saved = _saved(app, mentor.id)
    assert (saved.send_gap_seconds, saved.burst_size) == (30, 10)
    assert (saved.burst_pause_minutes, saved.daily_send_limit) == (8, 40)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("send_gap_seconds", "2", "Gap between sends must be from 5 to 600 seconds"),
        ("burst_size", "0", "Messages before a pause must be from 1 to 100 messages"),
        ("burst_pause_minutes", "abc", "Enter pause length as a whole number of minutes"),
        ("daily_send_limit", "5000", "Daily limit must be from 1 to 300 messages"),
        ("daily_send_limit", "", "Enter daily limit"),
    ],
)
def test_limits_are_checked(app, signed_in_client, mentor, field, value, message):
    html = signed_in_client.post("/profile/sending-safety", data=SAFETY | {field: value})
    assert message in html.get_data(as_text=True)
    assert _saved(app, mentor.id).daily_send_limit == 60


def test_new_settings_need_sign_in(client):
    for path in ("/profile/preferences", "/profile/sending-safety"):
        assert client.post(path).headers["Location"].startswith("/sign-in")
