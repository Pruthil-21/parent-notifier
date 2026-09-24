"""The admin overview, shown as the admin's home page."""

from flask import render_template, request

from parent_notifier.services.admin import overview
from parent_notifier.services.shared import departments, pagination


def overview_page():
    return render_template(
        "pages/admin/overview/index.html",
        overview=overview.overview(
            departments.canonical(request.args.get("department")),
            pagination.page_number(request.args.get("page")),
        ),
    )
