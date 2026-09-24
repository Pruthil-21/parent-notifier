"""The home workspace, the first page after signing in."""

from flask import Blueprint, render_template
from flask_login import current_user, login_required

from parent_notifier.services.academics.views import home_summary

bp = Blueprint("home", __name__)


@bp.get("/")
@login_required
def index():
    return render_template(
        "pages/academics/home/index.html", summary=home_summary.build(current_user.id)
    )
