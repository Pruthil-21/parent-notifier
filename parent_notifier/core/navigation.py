"""The main navigation pane: which sections exist and which one is current."""

from collections.abc import Callable
from dataclasses import dataclass

from flask import Flask, current_app, request, url_for

# A section's sub-items, such as each class under Classes: dicts with label, url, active.
ChildLinks = Callable[[], list[dict[str, object]]]


@dataclass(frozen=True)
class NavItem:
    icon: str
    label: str
    endpoint: str
    # Other blueprints whose pages count as this section, such as semesters for Classes.
    also_covers: tuple[str, ...] = ()

    @property
    def blueprints(self) -> tuple[str, ...]:
        return (self.endpoint.split(".", 1)[0], *self.also_covers)


NAV_ITEMS = (
    NavItem("home", "Home", "home.index"),
    NavItem(
        "classes",
        "Classes",
        "classes.index",
        also_covers=("semesters", "class_settings", "imports"),
    ),
    NavItem("person", "Profile", "profile.index"),
    NavItem("help", "Help", "help.index"),
)


def register_child_links(app: Flask, endpoint: str, links: ChildLinks) -> None:
    """Let the blueprint that owns a section list its sub-items without core knowing
    about classes or any other domain."""
    app.extensions.setdefault("nav_child_links", {})[endpoint] = links


def _item_context(item: NavItem) -> dict[str, object]:
    provider = current_app.extensions.get("nav_child_links", {}).get(item.endpoint)
    children = provider() if provider else []
    in_section = request.blueprint in item.blueprints
    return {
        "icon": item.icon,
        "label": item.label,
        "url": url_for(item.endpoint),
        "active": in_section,
        # The section link is the current page only when no sub-item is.
        "current": in_section and not any(child["active"] for child in children),
        "children": children,
    }


def navigation_context() -> dict[str, object]:
    """Only sections whose pages are registered appear, so the pane never links to a
    page that does not exist yet."""
    registered = current_app.view_functions
    items = [_item_context(item) for item in NAV_ITEMS if item.endpoint in registered]
    home_url = items[0]["url"] if items else "/"
    return {"nav_items": items, "home_url": home_url}


def init_navigation(app: Flask) -> None:
    app.context_processor(navigation_context)
