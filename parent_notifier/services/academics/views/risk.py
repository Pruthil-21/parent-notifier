"""Status bands for one student in one semester (PROJECT.md 6.1).

1. At risk: theory or practical attendance below the threshold in any subject.
2. Needs attention: no shortage, but a Mid-Sem below the pass mark, or absent, anywhere.
3. Doing well: everything else.
4. No data: in the semester, but no numbers yet.

Subjects whose Mid-Sem has not been held are judged on attendance alone. A subject out
of another total passes at the same share as the class rule: with 7 of 20 (35%), a
subject out of 25 passes at 8.75, so 9.
"""

from dataclasses import dataclass

AT_RISK = "at_risk"
NEEDS_ATTENTION = "needs_attention"
DOING_WELL = "doing_well"
NO_DATA = "no_data"
BANDS = (AT_RISK, NEEDS_ATTENTION, DOING_WELL, NO_DATA)
BAND_LABELS = {
    AT_RISK: "At risk",
    NEEDS_ATTENTION: "Needs attention",
    DOING_WELL: "Doing well",
    NO_DATA: "No data",
}


@dataclass(frozen=True)
class Rules:
    attendance_threshold: int
    midsem_pass_mark: int
    midsem_max: int


@dataclass(frozen=True)
class SubjectResult:
    subject: str
    theory: float | None = None
    practical: float | None = None
    marks: float | None = None
    absent: bool = False
    # The subject's own Mid-Sem total, when it is not the class's.
    out_of: int | None = None

    @property
    def has_data(self) -> bool:
        return self.absent or any(v is not None for v in (self.theory, self.practical, self.marks))


@dataclass(frozen=True)
class Shortage:
    subject: str
    component: str  # "Theory" or "Practical"
    percent: float


@dataclass(frozen=True)
class Fail:
    subject: str
    marks: float | None  # None when absent
    out_of: int = 20


def shortages(results: list[SubjectResult], rules: Rules) -> list[Shortage]:
    found = []
    for result in results:
        for component, value in (("Theory", result.theory), ("Practical", result.practical)):
            if value is not None and value < rules.attendance_threshold:
                found.append(Shortage(result.subject, component, value))
    return found


def marks_max(result: SubjectResult, rules: Rules) -> int:
    return result.out_of or rules.midsem_max


def below_pass(result: SubjectResult, rules: Rules) -> bool:
    """Below the pass mark's share of the subject's total, compared without rounding."""
    if result.marks is None:
        return False
    return result.marks * rules.midsem_max < rules.midsem_pass_mark * marks_max(result, rules)


def fails(results: list[SubjectResult], rules: Rules) -> list[Fail]:
    return [
        Fail(result.subject, None if result.absent else result.marks, marks_max(result, rules))
        for result in results
        if result.absent or below_pass(result, rules)
    ]


def band(results: list[SubjectResult], rules: Rules) -> str:
    if not any(result.has_data for result in results):
        return NO_DATA
    if shortages(results, rules):
        return AT_RISK
    if fails(results, rules):
        return NEEDS_ATTENTION
    return DOING_WELL


def lowest_attendance(results: list[SubjectResult]) -> Shortage | None:
    """The lowest theory or practical figure across subjects, whether short or not."""
    figures = [
        Shortage(result.subject, component, value)
        for result in results
        for component, value in (("Theory", result.theory), ("Practical", result.practical))
        if value is not None
    ]
    return min(figures, key=lambda figure: figure.percent, default=None)


def midsem_average(results: list[SubjectResult], rules: Rules) -> float | None:
    """Average of the Mid-Sem marks written so far, out of the class's total; a subject
    out of another total is scaled to it. Absences are not averaged in."""
    marks = [
        result.marks * rules.midsem_max / marks_max(result, rules)
        for result in results
        if result.marks is not None
    ]
    return round(sum(marks) / len(marks), 1) if marks else None
