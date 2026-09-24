import pytest
from flask import Blueprint

from parent_notifier import create_app
from parent_notifier.core import navigation
from parent_notifier.core.navigation import NavItem, navigation_context


@pytest.fixture
def app_with_sections(monkeypatch):
    monkeypatch.setattr(
        navigation,
        "NAV_ITEMS",
        (
            NavItem("home", "Start", "start.index"),
            NavItem("classes", "Reports", "reports.index"),
            NavItem("help", "Guide", "guide.index"),
        ),
    )
    app = create_app("testing")
    for name, path in (("start", "/start"), ("guide", "/guide")):
        blueprint = Blueprint(name, __name__)
        blueprint.add_url_rule(path, "index", lambda: "ok")
        app.register_blueprint(blueprint)
    return app


def test_only_registered_sections_are_listed(app_with_sections):
    with app_with_sections.test_request_context("/guide"):
        context = navigation_context()
    assert [item["label"] for item in context["nav_items"]] == ["Start", "Guide"]
    assert context["home_url"] == "/start"


def test_current_section_is_marked_active(app_with_sections):
    with app_with_sections.test_request_context("/guide"):
        items = {item["label"]: item["active"] for item in navigation_context()["nav_items"]}
    assert items == {"Start": False, "Guide": True}


def test_no_registered_sections_links_home_to_root(app, monkeypatch):
    monkeypatch.setattr(navigation, "NAV_ITEMS", (NavItem("add", "Reports", "reports.index"),))
    with app.test_request_context("/"):
        assert navigation_context() == {"nav_items": [], "home_url": "/"}


def test_sections_can_list_sub_items_and_mark_the_current_one(app_with_sections):
    navigation.register_child_links(
        app_with_sections,
        "guide.index",
        lambda: [
            {"label": "Part 1", "url": "/guide/1", "active": False},
            {"label": "Part 2", "url": "/guide/2", "active": True},
        ],
    )
    with app_with_sections.test_request_context("/guide"):
        guide = navigation_context()["nav_items"][1]
    assert [child["label"] for child in guide["children"]] == ["Part 1", "Part 2"]
    assert guide["active"] is True
    assert guide["current"] is False


def test_other_blueprints_can_count_as_a_section(monkeypatch):
    monkeypatch.setattr(
        navigation, "NAV_ITEMS", (NavItem("classes", "Guide", "guide.index", ("chapter",)),)
    )
    app = create_app("testing")
    for name, path in (("guide", "/guide"), ("chapter", "/chapter")):
        blueprint = Blueprint(name, __name__)
        blueprint.add_url_rule(path, "index", lambda: "ok")
        app.register_blueprint(blueprint)
    with app.test_request_context("/chapter"):
        [guide] = navigation_context()["nav_items"]
    assert guide["active"] is True
    assert guide["current"] is True


def test_long_sections_can_be_marked_filterable(app_with_sections, monkeypatch):
    monkeypatch.setattr(
        navigation, "NAV_ITEMS", (NavItem("help", "User guide", "guide.index", filterable=True),)
    )
    with app_with_sections.test_request_context("/guide"):
        [guide] = navigation_context()["nav_items"]
    assert guide["id"] == "user-guide" and guide["filterable"] is True


def test_a_section_can_claim_pages_from_another_blueprint(monkeypatch):
    monkeypatch.setattr(
        navigation,
        "NAV_ITEMS",
        (
            NavItem("people", "People", "guide.index", pages=("guide.person",), key="people"),
            NavItem("help", "Guide", "guide.index"),
        ),
    )
    app = create_app("testing")
    blueprint = Blueprint("guide", __name__)
    blueprint.add_url_rule("/guide", "index", lambda: "ok")
    blueprint.add_url_rule("/guide/<int:n>", "person", lambda n: "ok")
    app.register_blueprint(blueprint)
    for path, section in (("/guide/1", "People"), ("/guide", "Guide")):
        with app.test_request_context(path):
            active = [item["label"] for item in navigation_context()["nav_items"] if item["active"]]
        assert active == [section]
