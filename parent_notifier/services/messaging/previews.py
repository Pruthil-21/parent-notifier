"""Every message the popup may show for the students on screen, rendered in advance.

For each language there is the plain message and one with a note marker, which the
page swaps for whatever note the mentor types. The server renders the message again
when a send is logged, so what is stored never depends on the page.
"""

from dataclasses import dataclass

from parent_notifier.services.academics.views.semester_view import StudentRow
from parent_notifier.services.messaging.message_templates import LANGUAGES, render_message

# An invisible separator either side keeps the marker from matching anything typed.
NOTE_MARKER = "\u2063NOTE\u2063"


@dataclass(frozen=True)
class MessageContext:
    """What every message on the page shares: semester, rules, signature and college."""

    semester: int
    midsem_max: int
    mentor_name: str
    college_names: dict[str, str]  # language -> the college's name in that language


def render_for(row: StudentRow, context: MessageContext, language: str, note: str = "") -> str:
    return render_message(
        language,
        student_name=row.full_name,
        enrollment_no=row.enrollment_no,
        semester=context.semester,
        results=row.results,
        midsem_max=context.midsem_max,
        mentor_name=context.mentor_name,
        college_name=context.college_names[language],
        note=note,
    )


def messages_for(row: StudentRow, context: MessageContext) -> dict[str, dict[str, str]]:
    return {
        language: {
            "plain": render_for(row, context, language),
            "withNote": render_for(row, context, language, NOTE_MARKER),
        }
        for language in LANGUAGES
    }


def context_for(semester_number: int, midsem_max: int, mentor_name: str, config) -> MessageContext:
    return MessageContext(
        semester=semester_number,
        midsem_max=midsem_max,
        mentor_name=mentor_name,
        college_names={"en": config["COLLEGE_NAME"], "gu": config["COLLEGE_NAME_GU"]},
    )
