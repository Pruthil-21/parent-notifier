"""Everything the semester page shows: one row per student with its band, and the tiles.

Built from two queries (students, then all their results) however many students there
are, so a 120-student semester renders quickly.
"""

from dataclasses import dataclass, field

from sqlalchemy import select

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup, Result, Semester, SemesterSubject
from parent_notifier.services.academics import risk
from parent_notifier.services.academics.risk import Fail, Rules, Shortage, SubjectResult
from parent_notifier.services.shared.phone import format_for_display


@dataclass(frozen=True)
class StudentRow:
    id: int
    enrollment_no: str
    full_name: str
    parent_name: str
    phone_raw: str
    phone_e164: str | None
    status: str
    band: str
    results: list[SubjectResult]
    shortages: list[Shortage]
    fails: list[Fail]
    lowest: Shortage | None
    average: float | None

    @property
    def active(self) -> bool:
        return self.status == "active"


@dataclass
class SemesterView:
    rules: Rules
    subjects: list[str] = field(default_factory=list)
    rows: list[StudentRow] = field(default_factory=list)

    @property
    def active_rows(self) -> list[StudentRow]:
        return [row for row in self.rows if row.active]

    @property
    def tiles(self) -> dict[str, int]:
        """Counts per band for active students; left and detained students are left out."""
        counts = dict.fromkeys(risk.BANDS, 0)
        for row in self.active_rows:
            counts[row.band] += 1
        return counts


def rules_for(class_group: ClassGroup) -> Rules:
    return Rules(
        class_group.attendance_threshold, class_group.midsem_pass_mark, class_group.midsem_max
    )


def _results_by_student(semester: Semester) -> dict[int, dict[str, SubjectResult]]:
    query = (
        select(Result, SemesterSubject.name)
        .join(SemesterSubject, Result.semester_subject_id == SemesterSubject.id)
        .where(SemesterSubject.semester_id == semester.id)
    )
    found: dict[int, dict[str, SubjectResult]] = {}
    for result, subject in db.session.execute(query):
        found.setdefault(result.student_id, {})[subject] = SubjectResult(
            subject,
            result.theory_pct,
            result.practical_pct,
            result.midsem_marks,
            result.midsem_absent,
        )
    return found


def build(class_group: ClassGroup, semester: Semester) -> SemesterView:
    rules = rules_for(class_group)
    view = SemesterView(rules=rules, subjects=[subject.name for subject in semester.subjects])
    by_student = _results_by_student(semester)
    for student in sorted(semester.students, key=lambda s: s.enrollment_no):
        found = by_student.get(student.id, {})
        results = [found.get(name, SubjectResult(name)) for name in view.subjects]
        view.rows.append(
            StudentRow(
                id=student.id,
                enrollment_no=student.enrollment_no,
                full_name=student.full_name,
                parent_name=student.parent_name,
                phone_raw=student.phone_raw,
                phone_e164=student.phone_e164,
                status=student.status,
                band=risk.band(results, rules),
                results=results,
                shortages=risk.shortages(results, rules),
                fails=risk.fails(results, rules),
                lowest=risk.lowest_attendance(results),
                average=risk.midsem_average(results),
            )
        )
    return view


def find_row(view: SemesterView, student_id: int) -> StudentRow | None:
    return next((row for row in view.rows if row.id == student_id), None)


def _subject_payload(result: SubjectResult, rules: Rules) -> dict:
    def short(value):
        return value is not None and value < rules.attendance_threshold

    return {
        "name": result.subject,
        "theory": result.theory,
        "practical": result.practical,
        "marks": result.marks,
        "absent": result.absent,
        "theoryShort": short(result.theory),
        "practicalShort": short(result.practical),
        "fail": result.absent
        or (result.marks is not None and result.marks < rules.midsem_pass_mark),
    }


def popup_payload(rows: list[StudentRow], rules: Rules) -> list[dict]:
    """Plain data for the popup, for the rows on screen only. The page embeds it with
    tojson and the script writes it with textContent, so none of it is read as HTML."""
    return [
        {
            "id": row.id,
            "enrollment": row.enrollment_no,
            "name": row.full_name,
            "parent": row.parent_name,
            "phone": format_for_display(row.phone_e164) if row.phone_e164 else row.phone_raw,
            "phoneValid": row.phone_e164 is not None,
            "badge": row.band if row.active else row.status,
            "subjects": [_subject_payload(result, rules) for result in row.results],
        }
        for row in rows
    ]
