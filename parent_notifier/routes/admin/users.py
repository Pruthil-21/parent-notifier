"""The admin's accounts list and each account's page."""

from flask import Blueprint, abort, current_app, render_template, request, url_for

from parent_notifier.core.navigation import register_child_links
from parent_notifier.routes.admin.access import admin_required
from parent_notifier.services.admin import users
from parent_notifier.services.shared import activity, departments

bp = Blueprint("admin_users", __name__, url_prefix="/admin/users")

# The admin section's pages, in the order the navigation lists them.
ADMIN_PAGES = (
    ("Users", "admin_users.index", "admin_users"),
    ("Activity log", "admin_logs.index", "admin_logs"),
    ("Departments", "admin_settings.departments", "admin_settings.departments"),
    ("Announcement", "admin_settings.announcement", "admin_settings.announcement"),
    ("Settings", "admin_settings.index", "admin_settings.index"),
)


def _admin_links() -> list[dict[str, object]]:
    links = []
    for label, endpoint, covers in ADMIN_PAGES:
        if endpoint not in current_app.view_functions:
            continue
        active = request.endpoint == covers or request.blueprint == covers
        links.append({"label": label, "url": url_for(endpoint), "active": active})
    return links


bp.record_once(lambda state: register_child_links(state.app, "admin_users.index", _admin_links))


def load_account(account_id: int):
    account = users.get_account(account_id)
    if account is None:
        abort(404)
    return account


@bp.get("/")
@admin_required
def index():
    filters = users.Filters.from_args(request.args)
    return render_template(
        "pages/admin/users/index.html",
        filters=filters,
        page=users.account_page(filters),
        department_list=departments.names(),
    )


@bp.get("/<int:account_id>")
@admin_required
def detail(account_id: int):
    account = load_account(account_id)
    return render_template(
        "pages/admin/users/detail.html",
        account=account,
        classes=users.classes_of(account),
        recent=users.recent_activity(account),
        event_label=activity.event_label,
    )
