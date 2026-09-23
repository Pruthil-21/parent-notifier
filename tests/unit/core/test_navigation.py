import pytest
from flask import Blueprint

from parent_notifier import create_app
from parent_notifier.core.navigation import navigation_context


@pytest.fixture
def app_with_sections():
    app = create_app("testing")
    for name, path in (("home", "/"), ("help", "/help")):
        blueprint = Blueprint(name, __name__)
        blueprint.add_url_rule(path, "index", lambda: "ok")
        app.register_blueprint(blueprint)
    return app


def test_only_registered_sections_are_listed(app_with_sections):
    with app_with_sections.test_request_context("/help"):
        context = navigation_context()
    assert [item["label"] for item in context["nav_items"]] == ["Home", "Help"]
    assert context["home_url"] == "/"


def test_current_section_is_marked_active(app_with_sections):
    with app_with_sections.test_request_context("/help"):
        items = {item["label"]: item["active"] for item in navigation_context()["nav_items"]}
    assert items == {"Home": False, "Help": True}


def test_no_sections_yet_links_home_to_root(app):
    with app.test_request_context("/"):
        assert navigation_context() == {"nav_items": [], "home_url": "/"}
