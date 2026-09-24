from datetime import date

import pytest

from parent_notifier.services.academics.records.semester_numbers import current_for_batch, suggest


@pytest.mark.parametrize(
    ("admission_year", "today", "expected"),
    [
        (2023, date(2023, 7, 15), 1),
        (2023, date(2023, 12, 31), 1),
        (2023, date(2024, 1, 1), 2),
        (2023, date(2024, 6, 30), 2),
        (2023, date(2026, 9, 23), 7),
        (2023, date(2027, 3, 1), 8),
    ],
)
def test_batch_moves_up_a_semester_each_january_and_july(admission_year, today, expected):
    assert current_for_batch(admission_year, today) == expected


def test_suggestion_stays_between_1_and_12():
    assert current_for_batch(2026, date(2026, 3, 1)) == 1
    assert current_for_batch(2010, date(2026, 9, 1)) == 12


def test_suggests_the_semester_after_the_latest_added():
    assert suggest([3, 5, 4], 2023, date(2026, 9, 23)) == 6
    assert suggest([12], 2023, date(2026, 9, 23)) == 12


def test_first_semester_is_suggested_from_the_batch():
    assert suggest([], 2023, date(2026, 9, 23)) == 7
