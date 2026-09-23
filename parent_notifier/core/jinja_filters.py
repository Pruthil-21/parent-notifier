"""Template filters for values shown in more than one place."""

from flask import Flask

from parent_notifier.services.shared.phone import format_for_display


def init_jinja_filters(app: Flask) -> None:
    app.add_template_filter(format_for_display, "phone")
