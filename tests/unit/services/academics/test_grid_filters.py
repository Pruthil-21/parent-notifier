import pytest
from werkzeug.datastructures import MultiDict

from parent_notifier.services.academics.grid_filters import GridQuery, apply
from parent_notifier.services.academics.risk import Shortage
from parent_notifier.services.academics.semester_view import StudentRow


def row(enrollment, name, band="doing_well", status="active", lowest=None, parent="P"):
    shortage = Shortage("DBMS", "Theory", lowest) if lowest is not None else None
    return StudentRow(
        id=0,
        enrollment_no=enrollment,
        full_name=name,
        parent_name=parent,
        phone_raw="",
        phone_e164=None,
        status=status,
        band=band,
        results=[],
        shortages=[],
        fails=[],
        lowest=shortage,
        average=None,
    )


ROWS = [
    row("23CE002", "Riya Patel", "at_risk", lowest=70, parent="Kiran Patel"),
    row("23CE001", "Avi Shah", "doing_well", lowest=90),
    row("23CE003", "Om Desai", "needs_attention", lowest=80),
    row("23CE004", "Isha Joshi", "no_data"),
    row("23CE005", "Neel Bhatt", "doing_well", status="left", lowest=60),
]


def names(query: GridQuery) -> list[str]:
    return [r.full_name for r in apply(ROWS, query)]


def test_default_lists_active_students_by_enrollment():
    assert names(GridQuery()) == ["Avi Shah", "Riya Patel", "Om Desai", "Isha Joshi"]


@pytest.mark.parametrize(
    ("search", "expected"),
    [("riya", ["Riya Patel"]), ("KIRAN", ["Riya Patel"]), ("23ce003", ["Om Desai"]), ("zz", [])],
)
def test_search_covers_name_parent_and_enrollment(search, expected):
    assert names(GridQuery(search=search)) == expected


def test_status_filters():
    assert names(GridQuery(status="at_risk")) == ["Riya Patel"]
    assert names(GridQuery(status="inactive")) == ["Neel Bhatt"]
    assert names(GridQuery(status="inactive", search="riya")) == []


def test_sorting_by_name_and_attendance():
    assert names(GridQuery(sort="name")) == ["Avi Shah", "Isha Joshi", "Om Desai", "Riya Patel"]
    assert names(GridQuery(sort="attendance")) == [
        "Riya Patel",
        "Om Desai",
        "Avi Shah",
        "Isha Joshi",
    ]
    by_attendance_desc = names(GridQuery(sort="attendance", descending=True))
    assert by_attendance_desc == ["Avi Shah", "Om Desai", "Riya Patel", "Isha Joshi"]


def test_query_string_is_checked_against_fixed_lists():
    args = MultiDict({"q": "  riya   patel " + "x" * 200, "status": "hacked", "sort": "id;drop"})
    query = GridQuery.from_args(args)
    assert query.search.startswith("riya patel")
    assert len(query.search) == 100
    assert (query.status, query.sort, query.descending) == ("", "enrollment", False)
    assert GridQuery.from_args(MultiDict({"dir": "desc", "status": "at_risk"})).descending
