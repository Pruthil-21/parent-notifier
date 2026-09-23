"""Template filters for values shown in more than one place."""

from datetime import datetime

from flask import Flask, current_app

from parent_notifier.services.shared.formatting import format_date
from parent_notifier.services.shared.phone import format_for_display


def _local_date(moment: datetime | None) -> str:
    return format_date(moment, current_app.config["APP_TIMEZONE"])


def init_jinja_filters(app: Flask) -> None:
    app.add_template_filter(format_for_display, "phone")
    app.add_template_filter(_local_date, "date")
