import pytest

from parent_notifier.core.extensions import db
from parent_notifier.services.academics import semester_view
from parent_notifier.services.academics.risk import AT_RISK, DOING_WELL, NEEDS_ATTENTION, NO_DATA
from parent_notifier.services.imports.apply import apply_import
from parent_notifier.services.imports.sheet_parser import parse_sheet
from tests.factories.academics import make_class, make_semester
from tests.factories.accounts import make_mentor

pytestmark = pytest.mark.usefixtures("app_context")

HEADER = ["Enrollment No", "Student Name", "Parent Name", "Parent Phone", "DBMS", "OS"]


@pytest.fixture
def imported():
    mentor = make_mentor()
    class_group = make_class(mentor)
    semester = make_semester(class_group, 4)
    rows = [
        ["23CE003", "Riya", "Kiran", "9000000103", "Theory=70", "Theory=90"],
        ["23CE001", "Avi", "Mehul", "9000000101", "Theory=86,Marks=16", "Theory=80,Marks=AB"],
        ["23CE002", "Om", "Nilesh", "9000000102", "Theory=90,Marks=15", "Theory=88,Marks=12"],
        ["23CE004", "Isha", "Hetal", "9000000104", "", ""],
    ]
    sheet = parse_sheet([HEADER, *rows], 20)
    apply_import(class_group, semester, mentor.id, "s.xlsx", sheet, update_identity=False)
    return class_group, semester


def test_rows_are_in_enrollment_order_with_bands(imported):
    view = semester_view.build(*imported)
    assert view.subjects == ["DBMS", "OS"]
    assert [(row.enrollment_no, row.band) for row in view.rows] == [
        ("23CE001", NEEDS_ATTENTION),
        ("23CE002", DOING_WELL),
        ("23CE003", AT_RISK),
        ("23CE004", NO_DATA),
    ]


def test_row_details_for_the_grid(imported):
    avi, om, riya, _ = semester_view.build(*imported).rows
    assert (riya.lowest.subject, riya.lowest.percent) == ("DBMS", 70)
    assert [fail.subject for fail in avi.fails] == ["OS"]
    assert om.average == 13.5


def test_tiles_leave_out_left_and_detained_students(imported):
    class_group, semester = imported
    semester.students[0].status = "left"
    db.session.commit()
    view = semester_view.build(class_group, semester)
    assert len(view.active_rows) == 3
    assert sum(view.tiles.values()) == 3


def test_class_rules_change_the_bands(imported):
    class_group, semester = imported
    class_group.attendance_threshold = 95
    db.session.commit()
    bands = {row.band for row in semester_view.build(class_group, semester).rows}
    assert bands == {AT_RISK, NO_DATA}
