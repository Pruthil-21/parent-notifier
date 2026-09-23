"""Logging a send or skip from the student popup. JSON in, JSON out."""

from flask import Blueprint, abort, current_app, jsonify, request
from flask_login import current_user, login_required

from parent_notifier.core.extensions import limiter
from parent_notifier.routes.academics.semesters import load_semester
from parent_notifier.services.academics import semester_view
from parent_notifier.services.messaging import previews, send_log
from parent_notifier.services.messaging.message_templates import LANGUAGES, MAX_NOTE

bp = Blueprint(
    "messaging", __name__, url_prefix="/classes/<int:class_id>/sem/<int:number>/students"
)


def _error(message: str, status: int = 400):
    return jsonify(error=message), status


def _clean_note(raw: object) -> str | None:
    """Up to 500 characters; line breaks are fine, other control characters are not."""
    note = raw if isinstance(raw, str) else ""
    if len(note) > MAX_NOTE or any(not c.isprintable() and c != "\n" for c in note):
        return None
    return note.strip()


@bp.post("/<int:student_id>/log")
@login_required
@limiter.limit("30 per minute")
def log(class_id: int, number: int, student_id: int):
    class_group, semester = load_semester(class_id, number)
    row = semester_view.find_row(semester_view.build(class_group, semester), student_id)
    if row is None or not row.active:
        abort(404)
    body = request.get_json(silent=True) or {}
    status, language, note = body.get("status"), body.get("language"), _clean_note(body.get("note"))
    if status not in ("sent", "skipped") or language not in LANGUAGES or note is None:
        return _error("That request could not be used. Reload the page and try again.")
    if status == "sent" and row.phone_e164 is None:
        return _error("This parent has no valid mobile number. Edit the student to fix it.")
    context = previews.context_for(
        number, class_group.midsem_max, current_user.full_name, current_app.config
    )
    logged = send_log.log_send(
        semester, row, current_user.id, context, status=status, language=language, note=note
    )
    label = send_log.label(logged.mark, True, current_app.config["APP_TIMEZONE"])
    return jsonify(status=status, label=label, whatsappUrl=logged.whatsapp_url)
