import re

import pytest

ADMIN_PATHS = []


def _admin_rules(app):
    """Every admin address, with 1 for each id, so a new admin page is checked too."""
    rules = [rule for rule in app.url_map.iter_rules() if rule.rule.startswith("/admin")]
    return [
        (re.sub(r"<[^>]+>", "1", rule.rule), sorted(rule.methods - {"HEAD", "OPTIONS"}))
        for rule in rules
    ]


def test_every_admin_page_is_not_found_for_a_mentor(app, signed_in_client):
    rules = _admin_rules(app)
    assert rules  # the admin area exists
    for path, methods in rules:
        for method in methods:
            response = signed_in_client.open(path, method=method)
            assert response.status_code == 404, (method, path)


def test_the_admin_section_shows_to_the_admin(admin_client):
    assert 'title="Admin"' in admin_client.get("/").get_data(as_text=True)


def test_a_mentor_does_not_see_the_admin_section(signed_in_client):
    assert 'title="Admin"' not in signed_in_client.get("/").get_data(as_text=True)


@pytest.mark.parametrize("path", ["/admin/users/", "/admin/users/1"])
def test_admin_pages_need_sign_in(client, path):
    assert client.get(path).headers["Location"].startswith("/sign-in")
