"""Rendering the parent message from message_templates/parent_report.txt.

One message goes to every parent: each part in English, then in Gujarati. The template
is read fresh when it changes, so faculty can reword it without a restart. It renders
in Jinja's sandbox and as plain text: the output goes into a WhatsApp link, never into
a web page, and student data is only ever a value, never template code.
"""

from datetime import date
from pathlib import Path

from jinja2 import FileSystemLoader, StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

from parent_notifier.services.academics.views.risk import SubjectResult

TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "message_templates"
TEMPLATE = "parent_report.txt"
MAX_NOTE = 500
MISSING = "N/A"
ABSENT = "AB"
# How the message speaks of the student: "your daughter ... guide her". Without a known
# son or daughter it says "your ward".
WARDS = {
    "female": {"ward": "your daughter", "them": "her", "ward_gu": "આપની પુત્રી"},
    "male": {"ward": "your son", "them": "him", "ward_gu": "આપના પુત્ર"},
    None: {"ward": "your ward", "them": "your ward", "ward_gu": "આપના પાલ્ય"},
}

_environment = SandboxedEnvironment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=False,
    auto_reload=True,
    trim_blocks=True,
    lstrip_blocks=True,
    undefined=StrictUndefined,
)


def _number(value: float) -> str:
    return f"{value:g}"


def _subject(result: SubjectResult, midsem_max: int) -> dict:
    def percent(value):
        return MISSING if value is None else f"{_number(value)}%"

    if result.absent:
        marks = ABSENT
    elif result.marks is None:
        marks = f"--/{midsem_max}"
    else:
        marks = f"{_number(result.marks)}/{midsem_max}"
    return {
        "name": result.subject,
        "theory": percent(result.theory),
        "practical": percent(result.practical),
        "marks": marks,
    }


def signature(full_name: str) -> str:
    """ "Prof. Asha Patel"; the title is not doubled if the name already has it."""
    if full_name.lower().startswith(("prof.", "prof ")):
        return full_name
    return f"Prof. {full_name}"


def _day(value: date | None) -> str:
    """Dates as the college's letters write them, like 07-07-26."""
    return value.strftime("%d-%m-%y") if value else ""


def render_message(
    *,
    student_name: str,
    enrollment_no: str,
    semester: int,
    results: list[SubjectResult],
    midsem_max: int,
    mentor_name: str,
    college_name: str,
    gender: str | None = None,
    attendance_from: date | None = None,
    attendance_to: date | None = None,
    note: str = "",
) -> str:
    # The period shows only when both ends are known.
    known = attendance_from is not None and attendance_to is not None
    text = _environment.get_template(TEMPLATE).render(
        student_name=student_name,
        enrollment_no=enrollment_no,
        semester=semester,
        subjects=[_subject(result, midsem_max) for result in results],
        **WARDS.get(gender, WARDS[None]),
        from_date=_day(attendance_from) if known else "",
        to_date=_day(attendance_to) if known else "",
        note=note.strip(),
        mentor_name=signature(mentor_name),
        college_name=college_name,
    )
    return text.strip()
