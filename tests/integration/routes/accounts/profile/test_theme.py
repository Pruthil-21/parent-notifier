import pytest

from parent_notifier.core.extensions import db
from parent_notifier.models.accounts import Mentor


def _theme(app, mentor_id):
    with app.app_context():
        return db.session.get(Mentor, mentor_id).theme


def test_pages_follow_the_system_until_a_theme_is_chosen(client, signed_in_client):
    html = signed_in_client.get("/").get_data(as_text=True)
    assert '<html lang="en" data-theme="system">' in html
    assert 'aria-label="Theme: System"' in html
    assert 'value="system"\n                  data-label="System" aria-pressed="true"' in html


def test_menu_choice_without_javascript_returns_to_the_same_page(app, signed_in_client, mentor):
    data = {"theme": "dark", "next": "/classes?sort=name"}
    response = signed_in_client.post("/profile/theme", data=data)
    assert response.headers["Location"] == "/classes?sort=name"
    assert _theme(app, mentor.id) == "dark"
    html = signed_in_client.get("/").get_data(as_text=True)
    assert 'data-theme="dark"' in html and 'aria-label="Theme: Dark"' in html


def test_menu_choice_from_the_script_saves_without_a_page(app, signed_in_client, mentor):
    headers = {"Accept": "application/json"}
    response = signed_in_client.post("/profile/theme", data={"theme": "light"}, headers=headers)
    assert response.status_code == 204
    assert _theme(app, mentor.id) == "light"


@pytest.mark.parametrize("target", ["https://evil.example/", "//evil.example/", ""])
def test_next_stays_on_this_site(signed_in_client, target):
    response = signed_in_client.post("/profile/theme", data={"theme": "dark", "next": target})
    assert response.headers["Location"] == "/"


def test_unknown_theme_is_refused(app, signed_in_client, mentor):
    assert signed_in_client.post("/profile/theme", data={"theme": "neon"}).status_code == 400
    assert _theme(app, mentor.id) == "system"


def test_theme_needs_sign_in_and_public_pages_follow_the_system(client):
    assert client.post("/profile/theme").headers["Location"].startswith("/sign-in")
    assert 'data-theme="system"' in client.get("/sign-in").get_data(as_text=True)
