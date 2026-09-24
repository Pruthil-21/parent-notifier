import pytest

from parent_notifier.services.academics.views.risk import (
    AT_RISK,
    DOING_WELL,
    NEEDS_ATTENTION,
    NO_DATA,
    Fail,
    Rules,
    Shortage,
    SubjectResult,
    band,
    fails,
    lowest_attendance,
    midsem_average,
    shortages,
)

RULES = Rules(attendance_threshold=75, midsem_pass_mark=7, midsem_max=20)
GOOD = SubjectResult("DBMS", theory=86, practical=92, marks=16)


@pytest.mark.parametrize(
    ("results", "expected"),
    [
        ([GOOD], DOING_WELL),
        ([GOOD, SubjectResult("OS", theory=74.9)], AT_RISK),
        ([GOOD, SubjectResult("OS", theory=80, practical=70)], AT_RISK),
        ([GOOD, SubjectResult("OS", theory=80, marks=6)], NEEDS_ATTENTION),
        ([GOOD, SubjectResult("OS", theory=80, absent=True)], NEEDS_ATTENTION),
        ([SubjectResult("OS", theory=70, marks=3)], AT_RISK),
        ([SubjectResult("OS", theory=75, practical=75, marks=7)], DOING_WELL),
        ([SubjectResult("OS", theory=90)], DOING_WELL),
        ([SubjectResult("OS"), SubjectResult("CN")], NO_DATA),
        ([], NO_DATA),
    ],
    ids=[
        "all fine",
        "theory short",
        "practical short",
        "failed mid-sem",
        "absent",
        "shortage beats fail",
        "exactly at the limits",
        "mid-sem not held",
        "no numbers",
        "no subjects",
    ],
)
def test_bands(results, expected):
    assert band(results, RULES) == expected


def test_rules_come_from_the_class():
    strict = Rules(attendance_threshold=85, midsem_pass_mark=12, midsem_max=30)
    assert band([GOOD], strict) == DOING_WELL
    assert band([SubjectResult("OS", theory=80)], strict) == AT_RISK
    assert band([SubjectResult("OS", theory=90, marks=11)], strict) == NEEDS_ATTENTION


def test_shortages_and_fails_are_listed():
    results = [
        SubjectResult("DBMS", theory=70, practical=60, marks=5),
        SubjectResult("OS", theory=90, absent=True),
    ]
    assert shortages(results, RULES) == [
        Shortage("DBMS", "Theory", 70),
        Shortage("DBMS", "Practical", 60),
    ]
    assert fails(results, RULES) == [Fail("DBMS", 5), Fail("OS", None)]


def test_lowest_attendance_and_average():
    results = [GOOD, SubjectResult("OS", theory=80, practical=78, marks=11, absent=False)]
    assert lowest_attendance(results) == Shortage("OS", "Practical", 78)
    assert midsem_average(results) == 13.5
    assert lowest_attendance([SubjectResult("OS", marks=5)]) is None
    assert midsem_average([SubjectResult("OS", absent=True)]) is None
