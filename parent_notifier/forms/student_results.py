"""A student's figures for one semester, typed on the add and edit student page.

One row per subject of the semester, with Theory %, Practical %, Mid-Sem marks and
Absent. An empty box means no figure yet. The numbers follow the same rules as a sheet:
percentages from 0 to 100, and marks from 0 to the subject's own total.
"""

import re
from dataclasses import dataclass

from parent_notifier.models.academics import Result, Semester
from parent_notifier.services.imports.cell_parser import SubjectCell

_NUMBER = re.compile(r"^\d{1,3}(?:\.\d{1,2})?$")
# Longer entries are refused by the pattern; this only bounds what is shown back.
MAX_LENGTH = 20


@dataclass
class ResultRow:
    subject_id: int
    name: str
    total: int
    theory: str = ""
    practical: str = ""
    marks: str = ""
    absent: bool = False
    error: str | None = None

    def cell(self) -> SubjectCell:
        """The figures to save; call only once the row has no error."""
        return SubjectCell(
            theory=float(self.theory) if self.theory else None,
            practical=float(self.practical) if self.practical else None,
            marks=float(self.marks) if self.marks else None,
            absent=self.absent,
        )


def _text(value: float | None) -> str:
    return "" if value is None else f"{value:g}"


def rows_for(semester: Semester, class_max: int, saved: dict[int, Result]) -> list[ResultRow]:
    """The rows as saved, by subject id, for the page before anything is posted."""
    rows = []
    for subject in semester.subjects:
        result = saved.get(subject.id)
        rows.append(
            ResultRow(
                subject.id,
                subject.name,
                subject.midsem_max or class_max,
                theory=_text(result.theory_pct) if result else "",
                practical=_text(result.practical_pct) if result else "",
                marks=_text(result.midsem_marks) if result else "",
                absent=bool(result and result.midsem_absent),
            )
        )
    return rows


def _problem(row: ResultRow) -> str | None:
    percent = "a percentage from 0 to 100"
    for label, value, limit, wanted in (
        ("Theory", row.theory, 100, percent),
        ("Practical", row.practical, 100, percent),
        ("Mid-Sem", row.marks, row.total, f"marks from 0 to {row.total}"),
    ):
        if value and (not _NUMBER.match(value) or float(value) > limit):
            return f"{row.name}: {label} must be {wanted}"
    if row.absent and row.marks:
        return f"{row.name}: leave Mid-Sem empty when the student was absent"
    return None


def rows_from_form(formdata, semester: Semester, class_max: int) -> list[ResultRow]:
    """The posted rows, each checked. Rows are matched to the semester's own subjects by
    position, so a request can only ever reach this semester's subjects."""
    rows = []
    for index, subject in enumerate(semester.subjects):

        def value(part: str, index: int = index) -> str:
            return (formdata.get(f"r{index}-{part}") or "").strip()[:MAX_LENGTH]

        row = ResultRow(
            subject.id,
            subject.name,
            subject.midsem_max or class_max,
            theory=value("theory"),
            practical=value("practical"),
            marks=value("marks"),
            absent=bool(formdata.get(f"r{index}-absent")),
        )
        row.error = _problem(row)
        rows.append(row)
    return rows
