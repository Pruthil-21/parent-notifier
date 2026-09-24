"""Showing the announcement banner, and closing it."""

from flask import Blueprint, Flask, redirect, request
from flask_login import current_user, login_required

from parent_notifier.routes.accounts.sessions import safe_next
from parent_notifier.services.shared import announcements

bp = Blueprint("announcements", __name__)


@bp.post("/announcement/<int:announcement_id>/dismiss")
@login_required
def dismiss(announcement_id: int):
    announcements.dismiss(announcement_id, current_user)
    return redirect(safe_next(request.form.get("next")))


def _banner():
    """Read only by the signed-in layout, so other pages skip the query."""
    return announcements.visible_for(current_user) if current_user.is_authenticated else None


def init_announcements(app: Flask) -> None:
    app.add_template_global(_banner, "announcement_banner")
