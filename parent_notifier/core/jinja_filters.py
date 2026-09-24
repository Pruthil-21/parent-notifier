"""Template filters and globals for values shown in more than one place."""

from datetime import date, datetime

from flask import Flask, current_app, request, url_for

from parent_notifier.services.shared import departments
from parent_notifier.services.shared.formatting import format_date, format_date_time
from parent_notifier.services.shared.phone import format_for_display


def _local_date(moment: datetime | None) -> str:
    return format_date(moment, current_app.config["APP_TIMEZONE"])


def _local_date_time(moment: datetime) -> str:
    return format_date_time(moment, current_app.config["APP_TIMEZONE"])


def _url_with(**changes) -> str:
    """This page's address with some query values changed; None drops one. A filter
    change goes back to page one unless the page is what changes."""
    args = request.args.to_dict()
    if "page" not in changes:
        args.pop("page", None)
    args.update(changes)
    kept = {key: value for key, value in args.items() if value not in (None, "")}
    return url_for(request.endpoint, **(request.view_args or {}), **kept)


def _iso_day(value: str | None) -> str:
    """ "2026-07-07" as 07-07-26, as the college's letters write dates."""
    return date.fromisoformat(value).strftime("%d-%m-%y") if value else ""


def init_jinja_filters(app: Flask) -> None:
    app.add_template_filter(format_for_display, "phone")
    app.add_template_filter(_local_date, "date")
    app.add_template_filter(_local_date_time, "date_time")
    app.add_template_filter(_iso_day, "iso_day")
    # A function, so the list is read only on pages with a department field.
    app.add_template_global(departments.names, "department_names")
    app.add_template_global(_url_with, "url_with")
