"""Branded error pages. They say what happened and what to do next, and never show
internals such as stack traces or the requested address."""

from flask import Flask, current_app, render_template
from flask_wtf.csrf import CSRFError
from werkzeug.exceptions import HTTPException

ERROR_PAGES = {
    400: (
        "That request could not be used",
        "Something in what was sent did not look right. Go back and try again.",
    ),
    403: (
        "You do not have access to this page",
        "It belongs to another account. Go back to your home page.",
    ),
    404: (
        "Page not found",
        "The address may be mistyped, or the page may have moved. Check it, or go back to "
        "your home page.",
    ),
    413: ("The file is too large", None),
    429: ("Too many attempts", "Wait a few minutes, then try again."),
    500: (
        "Something went wrong on our side",
        "Try again in a moment. If it keeps happening, tell whoever runs Parent Notifier "
        "for your department.",
    ),
}


# A missing or stale CSRF token nearly always means a page left open across a restart or
# sign-out, so the 400 page tells the mentor how to recover instead of blaming the request.
EXPIRED_FORM = (
    "This form has expired",
    "Go back, reload the page and fill in the form again.",
)


def _upload_limit_message() -> str:
    limit_mb = current_app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
    return f"The file is larger than {limit_mb} MB. Upload a smaller file."


def render_error(error: HTTPException):
    code = error.code if error.code in ERROR_PAGES else 500
    title, message = EXPIRED_FORM if isinstance(error, CSRFError) else ERROR_PAGES[code]
    if code == 413:
        message = _upload_limit_message()
    html = render_template("pages/support/error.html", code=code, title=title, message=message)
    return html, code


def init_error_pages(app: Flask) -> None:
    for code in ERROR_PAGES:
        app.register_error_handler(code, render_error)
