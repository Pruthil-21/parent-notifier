"""The help page: filling the sheet, the statuses, sending, pacing and the wording."""

from flask import Blueprint, current_app, render_template
from flask_login import current_user, login_required

from parent_notifier.services.messaging.pacing import settings_for

bp = Blueprint("help", __name__)


@bp.get("/help")
@login_required
def index():
    return render_template(
        "pages/support/help.html",
        pacing=settings_for(current_user),
        max_upload_mb=current_app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024),
    )
