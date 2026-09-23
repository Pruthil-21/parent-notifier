"""Which semester number to suggest when a mentor adds one."""

from collections.abc import Iterable
from datetime import date

from parent_notifier.models.academics import MAX_SEMESTER, MIN_SEMESTER

# Odd semesters run from July to December, even ones from January to June.
ODD_SEMESTER_STARTS = 7


def current_for_batch(admission_year: int, today: date) -> int:
    """The semester a batch should be in today: a 2023 batch is in Sem 7 in Sep 2026."""
    years_in = today.year - admission_year
    number = years_in * 2 + (1 if today.month >= ODD_SEMESTER_STARTS else 0)
    return max(MIN_SEMESTER, min(number, MAX_SEMESTER))


def suggest(existing: Iterable[int], admission_year: int, today: date) -> int:
    """The one after the latest semester added, or the batch's current semester when
    none has been added yet."""
    numbers = list(existing)
    if numbers:
        return min(max(numbers) + 1, MAX_SEMESTER)
    return current_for_batch(admission_year, today)
