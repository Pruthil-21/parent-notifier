"""Logging a send or skip from the student popup. JSON in, JSON out."""

from flask import Blueprint, abort, current_app, jsonify, request
from flask_login import current_user, login_required

from parent_notifier.core.extensions import limiter
from parent_notifier.routes.academics.semesters import load_semester
from parent_notifier.services.academics import semester_view
from parent_notifier.services.messaging import pacing, previews, send_log
from parent_notifier.services.messaging.message_templates import LANGUAGES, MAX_NOTE

bp = Blueprint(
    "messaging", __name__, url_prefix="/classes/<int:class_id>/sem/<int:number>/students"
)


def _error(message: str, status: int = 400):
    return jsonify(error=message), status


def pacing_json(decision: pacing.Decision) -> dict:
    return {
        "waitSeconds": decision.wait_seconds,
        "reason": decision.reason,
        "sentToday": decision.sent_today,
        "dailyLimit": decision.daily_limit,
    }


def _check_pacing(timezone: str):
    """The daily limit is enforced here. The gap and burst pause are enforced by the page;
    a send inside them is logged, not refused, so a slow network never locks anyone out."""
    decision = pacing.status_for(current_user, timezone)
    if decision.reason == pacing.DAILY:
        message = (
            f"You have sent today's limit of {decision.daily_limit} messages. "
            "Sending opens again tomorrow."
        )
        return jsonify(error=message, pacing=pacing_json(decision)), 409
    if decision.wait_seconds:
        current_app.logger.warning(
            "Send %ss inside the %s wait by mentor %s",
            decision.wait_seconds,
            decision.reason,
            current_user.id,
        )
    return None


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
    timezone = current_app.config["APP_TIMEZONE"]
    if status == "sent" and (refused := _check_pacing(timezone)):
        return refused
    context = previews.context_for(
        number, class_group.midsem_max, current_user.full_name, current_app.config
    )
    logged = send_log.log_send(
        semester, row, current_user.id, context, status=status, language=language, note=note
    )
    return jsonify(
        status=status,
        label=send_log.label(logged.mark, True, timezone),
        whatsappUrl=logged.whatsapp_url,
        pacing=pacing_json(pacing.status_for(current_user, timezone)),
    )
