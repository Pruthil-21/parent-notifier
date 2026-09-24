import re


def test_help_needs_sign_in(client):
    assert client.get("/help").headers["Location"].startswith("/sign-in")


def test_help_is_in_the_navigation_and_covers_each_topic(signed_in_client):
    html = signed_in_client.get("/help").get_data(as_text=True)
    assert re.search(r'href="/help" title="Help"\s+aria-current="page"', html)
    for anchor in ("sheet", "statuses", "sending", "pacing", "wording"):
        assert f'<a href="#{anchor}">' in html and f'id="{anchor}"' in html
    assert 'href="/sheet-format.xlsx" download>Download sheet format</a>' in html
    assert "up to 5 MB" in html
    assert "<code>{{ student_name }}</code>" in html


def test_pacing_section_shows_the_mentors_own_settings(app, mentor, signed_in_client):
    from parent_notifier.core.extensions import db
    from parent_notifier.models.accounts import Mentor

    with app.app_context():
        saved = db.session.get(Mentor, mentor.id)
        saved.send_gap_seconds, saved.daily_send_limit = 45, 25
        db.session.commit()
    html = signed_in_client.get("/help").get_data(as_text=True)
    assert "45 seconds between messages" in html
    assert "a 5-minute pause after every 15 messages" in html
    assert "at most 25 messages a day" in html


def test_home_links_to_filling_the_sheet(signed_in_client):
    html = signed_in_client.get("/").get_data(as_text=True)
    assert '<a href="/help#sheet">How to fill the sheet</a>' in html
