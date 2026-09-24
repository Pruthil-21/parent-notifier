"""The search page, reached from the box in the top bar."""

from flask import Blueprint, render_template, request
from flask_login import current_user, login_required

from parent_notifier.core.extensions import limiter
from parent_notifier.services.shared import search

bp = Blueprint("search", __name__)


@bp.get("/search")
@login_required
@limiter.limit("60 per minute")
def index():
    query = search.clean(request.args.get("q"))
    return render_template(
        "pages/search/index.html",
        query=query,
        results=search.run(query, current_user),
        min_length=search.MIN_LENGTH,
        limit=search.LIMIT,
    )
