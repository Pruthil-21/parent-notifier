"""The main navigation pane: which sections exist and which one is current."""

from dataclasses import dataclass

from flask import Flask, current_app, request, url_for


@dataclass(frozen=True)
class NavItem:
    icon: str
    label: str
    endpoint: str

    @property
    def blueprint(self) -> str:
        return self.endpoint.split(".", 1)[0]


NAV_ITEMS = (
    NavItem("home", "Home", "home.index"),
    NavItem("classes", "Classes", "classes.index"),
    NavItem("person", "Profile", "profile.index"),
    NavItem("help", "Help", "help.index"),
)


def navigation_context() -> dict[str, object]:
    """Only sections whose pages are registered appear, so the pane never links to a
    page that does not exist yet."""
    registered = current_app.view_functions
    items = [
        {
            "icon": item.icon,
            "label": item.label,
            "url": url_for(item.endpoint),
            "active": request.blueprint == item.blueprint,
        }
        for item in NAV_ITEMS
        if item.endpoint in registered
    ]
    home_url = items[0]["url"] if items else "/"
    return {"nav_items": items, "home_url": home_url}


def init_navigation(app: Flask) -> None:
    app.context_processor(navigation_context)
