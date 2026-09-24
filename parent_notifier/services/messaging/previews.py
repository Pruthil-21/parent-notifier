"""Every message the popup may show for the students on screen, rendered in advance.

There is the plain message and one with a note marker, which the page swaps for
whatever note the mentor types. The server renders the message again when a send is
logged, so what is stored never depends on the page.
"""

from dataclasses import dataclass
from datetime import date

from parent_notifier.services.academics.views.semester_view import StudentRow
from parent_notifier.services.messaging.message_templates import render_message

# An invisible separator either side keeps the marker from matching anything typed.
NOTE_MARKER = "\u2063NOTE\u2063"


@dataclass(frozen=True)
class MessageContext:
    """What every message on the page shares: semester, rules, signature and college."""

    semester: int
    midsem_max: int
    mentor_name: str
    college_name: str
    attendance_from: date | None = None
    attendance_to: date | None = None


def render_for(row: StudentRow, context: MessageContext, note: str = "") -> str:
    return render_message(
        student_name=row.full_name,
        enrollment_no=row.enrollment_no,
        semester=context.semester,
        results=row.results,
        midsem_max=context.midsem_max,
        mentor_name=context.mentor_name,
        college_name=context.college_name,
        gender=row.gender,
        attendance_from=context.attendance_from,
        attendance_to=context.attendance_to,
        note=note,
    )


def messages_for(row: StudentRow, context: MessageContext) -> dict[str, str]:
    return {"plain": render_for(row, context), "withNote": render_for(row, context, NOTE_MARKER)}


def context_for(semester, midsem_max: int, mentor_name: str, config) -> MessageContext:
    return MessageContext(
        semester=semester.number,
        midsem_max=midsem_max,
        mentor_name=mentor_name,
        college_name=config["COLLEGE_NAME"],
        attendance_from=semester.attendance_from,
        attendance_to=semester.attendance_to,
    )
