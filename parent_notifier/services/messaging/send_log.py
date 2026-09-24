"""Recording sends and skips, and reading each parent's message status."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import Semester
from parent_notifier.models.messaging import SendLog
from parent_notifier.services.academics.views.semester_view import StudentRow
from parent_notifier.services.messaging import previews
from parent_notifier.services.messaging.whatsapp_links import whatsapp_link
from parent_notifier.services.shared import clock
from parent_notifier.services.shared.formatting import format_day_month


@dataclass(frozen=True)
class Mark:
    status: str  # "sent" or "skipped"
    at: datetime


def record(semester: Semester, student_id: int, mentor_id: int, **fields) -> SendLog:
    entry = SendLog(
        semester_id=semester.id,
        student_id=student_id,
        mentor_id=mentor_id,
        round=semester.current_round,
        created_at=clock.now(),
        **fields,
    )
    db.session.add(entry)
    db.session.commit()
    return entry


def marks_for(semester: Semester) -> dict[int, Mark]:
    """Each student's latest send or skip for the semester's current import. Students
    missing from the result are pending."""
    query = (
        select(SendLog.student_id, SendLog.status, SendLog.created_at)
        .where(SendLog.semester_id == semester.id, SendLog.round == semester.current_round)
        .order_by(SendLog.id)
    )
    return {row.student_id: Mark(row.status, row.created_at) for row in db.session.execute(query)}


def label(mark: Mark | None, has_phone: bool, timezone: str) -> str:
    """What the grid and popup say: "Sent 24 Sep", "Skipped", "Pending" or "No phone"."""
    if mark is not None:
        return f"Sent {format_day_month(mark.at, timezone)}" if mark.status == "sent" else "Skipped"
    return "Pending" if has_phone else "No phone"


@dataclass(frozen=True)
class Logged:
    mark: Mark
    whatsapp_url: str | None


def log_send(
    semester: Semester,
    row: StudentRow,
    mentor_id: int,
    context: previews.MessageContext,
    *,
    status: str,
    language: str,
    note: str,
) -> Logged:
    """Store a send or skip. For a send the server renders the message itself, and the
    link it returns carries exactly the text that was stored."""
    message = previews.render_for(row, context, language, note) if status == "sent" else ""
    entry = record(
        semester, row.id, mentor_id, status=status, language=language, note=note, message=message
    )
    link = whatsapp_link(row.phone_e164, message) if status == "sent" else None
    return Logged(Mark(entry.status, entry.created_at), link)


def pending_ids(rows: list[StudentRow], marks: dict[int, Mark]) -> set[int]:
    """Active students with a valid number and no send or skip for the current import."""
    return {row.id for row in rows if row.active and row.phone_e164 and row.id not in marks}
