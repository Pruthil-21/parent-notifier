"""The admin overview, shown as the admin's home page."""

from flask import render_template, request

from parent_notifier.services.admin import overview
from parent_notifier.services.shared import departments


def overview_page():
    filters = overview.Filters.from_args(request.args)
    page = (overview.mentor_page if filters.view == "mentors" else overview.class_page)(filters)
    return render_template(
        "pages/admin/overview/index.html",
        filters=filters,
        page=page,
        totals=overview.totals(),
        department_list=departments.names(),
    )
