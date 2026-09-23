import pytest
from flask import Blueprint, render_template_string

from parent_notifier import create_app
from parent_notifier.core import navigation
from parent_notifier.core.navigation import NavItem

PAGE = '{% extends "layouts/app.html" %}{% block title %}Classes{% endblock %}'
PAGE += "{% block content %}<p>{{ note }}</p>{% endblock %}"


@pytest.fixture
def app(monkeypatch):
    """A made-up section, so these tests do not depend on which real pages exist."""
    monkeypatch.setattr(navigation, "NAV_ITEMS", (NavItem("classes", "Reports", "reports.index"),))
    app = create_app("testing")
    blueprint = Blueprint("reports", __name__)
    blueprint.add_url_rule("/reports", "index", lambda: render_template_string(PAGE, note="x"))
    app.register_blueprint(blueprint)
    return app


def render(app, **context):
    with app.test_request_context("/reports"):
        return render_template_string(PAGE, **context)


def test_layout_has_landmarks_and_skip_link(app):
    html = render(app, note="Hello")
    assert '<a class="skip-link" href="#main">Skip to main content</a>' in html
    assert '<header class="top-bar">' in html
    assert '<nav id="nav-pane" class="nav-pane" aria-label="Main">' in html
    assert '<main id="main" class="app-main" tabindex="-1">' in html
    assert "<title>Classes · Parent Notifier</title>" in html


def test_current_section_is_marked_for_assistive_tech(app):
    html = render(app, note="x")
    assert 'href="/reports" title="Reports"' in html
    assert 'aria-current="page"' in html


def test_theme_defaults_to_system(app):
    assert '<html lang="en" data-theme="system">' in render(app, note="x")


def test_page_content_is_escaped(app):
    html = render(app, note="<script>alert(1)</script>")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_layout_scripts_and_styles_are_served(app):
    client = app.test_client()
    html = client.get("/reports").get_data(as_text=True)
    for path in ("/static/css/app.css", "/static/js/shell/nav-pane.js"):
        assert path in html
        assert client.get(path).status_code == 200
