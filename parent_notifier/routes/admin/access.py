"""The checks admin pages run: the admin only, and for actions that change another
account, a password confirmed in the last 15 minutes (like GitHub's sudo mode)."""

from datetime import timedelta
from functools import wraps
from urllib.parse import urlsplit

from flask import abort, flash, redirect, request, session, url_for
from flask_login import current_user, login_required

from parent_notifier.services.shared import clock

CONFIRMED_FOR = timedelta(minutes=15)
_CONFIRMED_UNTIL = "admin_confirmed_until"


def admin_required(view):
    @wraps(view)
    @login_required
    def checked(*args, **kwargs):
        if not current_user.is_admin:
            abort(404)
        return view(*args, **kwargs)

    return checked


def password_recently_confirmed() -> bool:
    until = session.get(_CONFIRMED_UNTIL)
    return until is not None and clock.now().timestamp() < until


def remember_confirmation() -> None:
    session[_CONFIRMED_UNTIL] = (clock.now() + CONFIRMED_FOR).timestamp()


def _page_before() -> str:
    """The page the form was on, as a path on this site, to come back to."""
    parts = urlsplit(request.referrer or "")
    if parts.netloc == request.host and parts.path.startswith("/"):
        return parts.path + (f"?{parts.query}" if parts.query else "")
    return url_for("home.index")


def confirmed_password_required(view):
    """For admin actions that change another account. Without a recent confirmation,
    nothing happens: the admin confirms their password, then repeats the action."""

    @wraps(view)
    @admin_required
    def checked(*args, **kwargs):
        if not password_recently_confirmed():
            flash("Confirm your password, then do that again.", "info")
            return redirect(url_for("admin_users.confirm_password", next=_page_before()))
        return view(*args, **kwargs)

    return checked
