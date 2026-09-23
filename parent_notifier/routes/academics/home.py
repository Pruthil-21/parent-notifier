"""The home workspace, the first page after signing in."""

from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint("home", __name__)


@bp.get("/")
@login_required
def index():
    return render_template("pages/academics/home/index.html")
