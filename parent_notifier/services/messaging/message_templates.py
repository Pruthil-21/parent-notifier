"""Rendering the parent message from the template files in message_templates/.

Templates are read fresh when they change, so faculty can reword them without a
restart. They render in Jinja's sandbox and as plain text: the output goes into a
WhatsApp link, never into a web page, and student data is only ever a value, never
template code.
"""

from pathlib import Path

from jinja2 import FileSystemLoader, StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

from parent_notifier.services.academics.risk import SubjectResult

TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "message_templates"
LANGUAGES = {"en": "English"}
MAX_NOTE = 500
_WORDS = {
    "en": {"missing": "N/A", "absent": "AB", "title": "Prof."},
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


def _subject(result: SubjectResult, midsem_max: int, words: dict) -> dict:
    def percent(value):
        return words["missing"] if value is None else f"{_number(value)}%"

    if result.absent:
        marks = words["absent"]
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


def signature(full_name: str, language: str) -> str:
    """ "Prof. Asha Patel"; the title is not doubled if the name already has it."""
    title = _WORDS[language]["title"]
    if full_name.lower().startswith(("prof.", "prof ", title.lower())):
        return full_name
    return f"{title} {full_name}"


def render_message(
    language: str,
    *,
    student_name: str,
    enrollment_no: str,
    semester: int,
    results: list[SubjectResult],
    midsem_max: int,
    mentor_name: str,
    college_name: str,
    note: str = "",
) -> str:
    words = _WORDS[language]
    template = _environment.get_template(f"parent_report.{language}.txt")
    text = template.render(
        student_name=student_name,
        enrollment_no=enrollment_no,
        semester=semester,
        subjects=[_subject(result, midsem_max, words) for result in results],
        note=note.strip(),
        mentor_name=signature(mentor_name, language),
        college_name=college_name,
    )
    return text.strip()
