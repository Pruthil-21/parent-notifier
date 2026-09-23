"""Status bands for one student in one semester (PROJECT.md 6.1).

1. At risk: theory or practical attendance below the threshold in any subject.
2. Needs attention: no shortage, but a Mid-Sem below the pass mark, or absent, anywhere.
3. Doing well: everything else.
4. No data: in the semester, but no numbers yet.

Subjects whose Mid-Sem has not been held are judged on attendance alone.
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


def shortages(results: list[SubjectResult], rules: Rules) -> list[Shortage]:
    found = []
    for result in results:
        for component, value in (("Theory", result.theory), ("Practical", result.practical)):
            if value is not None and value < rules.attendance_threshold:
                found.append(Shortage(result.subject, component, value))
    return found


def fails(results: list[SubjectResult], rules: Rules) -> list[Fail]:
    return [
        Fail(result.subject, None if result.absent else result.marks)
        for result in results
        if result.absent or (result.marks is not None and result.marks < rules.midsem_pass_mark)
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


def midsem_average(results: list[SubjectResult]) -> float | None:
    """Average of the Mid-Sem marks written so far; absences are not averaged in."""
    marks = [result.marks for result in results if result.marks is not None]
    return round(sum(marks) / len(marks), 1) if marks else None
