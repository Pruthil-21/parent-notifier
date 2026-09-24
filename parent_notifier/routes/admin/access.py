"""The one check every admin page runs, so none can forget it."""

from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def admin_required(view):
    @wraps(view)
    @login_required
    def checked(*args, **kwargs):
        if not current_user.is_admin:
            abort(404)
        return view(*args, **kwargs)

    return checked
