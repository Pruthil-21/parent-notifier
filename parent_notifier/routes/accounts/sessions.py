"""What the account pages keep in the signed-in session, and where they send mentors next."""

from urllib.parse import urlsplit

from flask import redirect, session, url_for
from flask_login import login_user
from werkzeug.wrappers import Response

from parent_notifier.models.accounts import Mentor

_PENDING_CODE = "pending_recovery_code"
_AFTER_CODE = "after_recovery_code"
# Where Continue on the recovery code page may lead; the session holds a key, not a URL.
_AFTER_CODE_ENDPOINTS = {"home": "home.index", "profile": "profile.index"}


def start_session(mentor: Mentor, remember: bool = False) -> None:
    """Nothing from before sign-in carries over into the signed-in session."""
    session.clear()
    login_user(mentor, remember=remember)


def safe_next(target: str | None) -> str:
    """Follow `next` only to a path on this site. Scheme-relative URLs, backslashes and
    control characters (browsers drop tabs, so "/<tab>/x" becomes "//x") all go home."""
    if (
        target
        and target.startswith("/")
        and not target.startswith("//")
        and "\\" not in target
        and all(ord(char) >= 32 for char in target)
    ):
        parts = urlsplit(target)
        if not parts.scheme and not parts.netloc:
            return target
    return url_for("home.index")


def show_recovery_code(code: str, then: str = "home") -> Response:
    """Send the mentor to the page that shows a new code. The plain code stays in the
    session (signed, HttpOnly, never cached) only until they confirm they saved it."""
    session[_PENDING_CODE] = code
    session[_AFTER_CODE] = then if then in _AFTER_CODE_ENDPOINTS else "home"
    return redirect(url_for("registration.recovery_code"))


def pending_recovery_code() -> str | None:
    return session.get(_PENDING_CODE)


def finish_recovery_code() -> str:
    """Forget the plain code and return the URL Continue leads to."""
    session.pop(_PENDING_CODE, None)
    then = session.pop(_AFTER_CODE, "home")
    return url_for(_AFTER_CODE_ENDPOINTS.get(then, "home.index"))
