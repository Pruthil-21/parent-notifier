"""The main navigation pane: which sections exist and which one is current."""

import re
from collections.abc import Callable
from dataclasses import dataclass

from flask import Flask, current_app, request, url_for
from flask_login import current_user

# A section's sub-items, such as each class under Classes: links, headings and groups
# made by nav_link(), nav_heading() and nav_group(). Each has "active", true when it is,
# or holds, the current page.
ChildLinks = Callable[[], list[dict[str, object]]]


def nav_link(label: str, url: str, active: bool = False, note: str | None = None) -> dict:
    """`note` is a quiet detail after the label, such as a class's batch year."""
    return {"kind": "link", "label": label, "url": url, "active": active, "note": note}


def nav_heading(label: str) -> dict:
    """A small heading over the links after it, such as "2025 batch"; it does not fold."""
    return {"kind": "heading", "label": label, "active": False}


def nav_group(
    group_id: str,
    label: str,
    children: list[dict],
    url: str | None = None,
    current: bool = False,
    open_by_default: bool = True,
) -> dict:
    """A foldable group, such as a department. With `url` its label is also a link, and
    `current` marks that link as the page being shown."""
    return {
        "kind": "group",
        "id": group_id,
        "label": label,
        "url": url,
        "current": current,
        "open": open_by_default,
        "children": children,
        "active": current or any(child["active"] for child in children),
    }


def slug(text: str) -> str:
    """A name made safe for an element id, such as "computer-engineering"."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "group"


@dataclass(frozen=True)
class NavItem:
    icon: str
    label: str
    endpoint: str
    # Other blueprints whose pages count as this section, such as semesters for Classes.
    also_covers: tuple[str, ...] = ()
    # Shown only to the admin.
    admin_only: bool = False
    # Its sub-items can be narrowed by typing, for sections that grow long.
    filterable: bool = False
    # Pages that belong here although their blueprint is another section's, such as a
    # mentor's account page under Mentors rather than Admin. A section that lists pages
    # does not also claim its own link's blueprint.
    pages: tuple[str, ...] = ()
    # Names the section when two share a link; sub-items are registered under it.
    key: str = ""

    @property
    def blueprints(self) -> tuple[str, ...]:
        if self.pages:
            return self.also_covers
        return (self.endpoint.split(".", 1)[0], *self.also_covers)

    @property
    def section_key(self) -> str:
        return self.key or self.endpoint


NAV_ITEMS = (
    NavItem("home", "Home", "home.index"),
    NavItem(
        "classes",
        "Classes",
        "classes.index",
        also_covers=("semesters", "class_settings", "imports", "import_undo", "students"),
        filterable=True,
    ),
    NavItem(
        "people",
        "Mentors",
        "admin_users.index",
        admin_only=True,
        filterable=True,
        pages=(
            "admin_users.detail",
            "admin_users.edit",
            "admin_users.reset_password",
            "admin_users.transfer",
            "admin_users.delete",
            "admin_classes.open_class",
            "admin_classes.workspace",
            "admin_classes.student",
        ),
        key="mentors",
    ),
    NavItem(
        "admin",
        "Admin",
        "admin_users.index",
        also_covers=("admin_logs", "admin_settings", "admin_classes"),
        admin_only=True,
    ),
    NavItem("person", "Profile", "profile.index"),
    NavItem("help", "Help", "help.index"),
)


def register_child_links(app: Flask, section: str, links: ChildLinks) -> None:
    """Let the blueprint that owns a section list its sub-items without core knowing
    about classes or any other domain. `section` is the item's key, or its endpoint."""
    app.extensions.setdefault("nav_child_links", {})[section] = links


def _item_context(item: NavItem, claimed_by: NavItem | None) -> dict[str, object]:
    provider = current_app.extensions.get("nav_child_links", {}).get(item.section_key)
    children = provider() if provider else []
    # A page another section claims belongs to that section only.
    claimed = claimed_by is not None
    in_section = item is claimed_by if claimed else request.blueprint in item.blueprints
    return {
        # Names the section in the page, for its folding and filter controls.
        "id": item.label.lower().replace(" ", "-"),
        "icon": item.icon,
        "label": item.label,
        "url": url_for(item.endpoint),
        "active": in_section,
        # The section link is the current page only when no sub-item is.
        "current": in_section and not any(child["active"] for child in children),
        "children": children,
        "filterable": item.filterable,
    }


def navigation_context() -> dict[str, object]:
    """Only sections whose pages are registered appear, so the pane never links to a
    page that does not exist yet."""
    registered = current_app.view_functions
    is_admin = current_user.is_authenticated and current_user.is_admin
    shown = [
        item
        for item in NAV_ITEMS
        if item.endpoint in registered and (is_admin or not item.admin_only)
    ]
    claimed_by = next((item for item in shown if request.endpoint in item.pages), None)
    items = [_item_context(item, claimed_by) for item in shown]
    home_url = items[0]["url"] if items else "/"
    return {"nav_items": items, "home_url": home_url}


def init_navigation(app: Flask) -> None:
    app.context_processor(navigation_context)
