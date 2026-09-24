"""The activity log page for the admin."""

from flask import Blueprint, current_app, render_template, request

from parent_notifier.models.activity import CATEGORIES
from parent_notifier.routes.admin.access import admin_required
from parent_notifier.services.admin import logs
from parent_notifier.services.shared import activity, departments

bp = Blueprint("admin_logs", __name__, url_prefix="/admin/activity")


@bp.get("/")
@admin_required
def index():
    logs.purge_old()
    filters = logs.Filters.from_args(request.args)
    return render_template(
        "pages/admin/logs/index.html",
        filters=filters,
        page=logs.entry_page(filters, current_app.config["APP_TIMEZONE"]),
        categories=[(key, activity.CATEGORY_LABELS[key]) for key in CATEGORIES],
        category_labels=activity.CATEGORY_LABELS,
        events=activity.EVENTS,
        event_label=activity.event_label,
        describe=logs.describe,
        department_list=departments.names(),
    )
