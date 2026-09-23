import pytest

from parent_notifier.services.imports.cell_parser import SubjectCell
from parent_notifier.services.imports.sheet_parser import parse_sheet
from tests.factories.workbooks import HEADER, sheet_rows

ID = ["23CE001", "Avi Shah", "Mehul Shah", "90000 00101"]


def parse(grid, midsem_max=20):
    return parse_sheet([[str(value) for value in row] for row in grid], midsem_max)


def test_students_and_subjects_are_read():
    sheet = parse(sheet_rows())
    assert sheet.errors == []
    assert sheet.subjects == ["DBMS", "OS"]
    first = sheet.rows[0]
    assert (first.row_number, first.enrollment_no, first.phone_e164) == (
        2,
        "23CE001",
        "+919000000101",
    )
    assert first.cells["DBMS"] == SubjectCell(theory=86, practical=92, marks=16)
    assert first.cells["OS"] == SubjectCell(theory=79, absent=True)


def test_title_rows_above_the_header_are_skipped():
    grid = [["GCET CE-A Sem 4"], [], *sheet_rows()]
    sheet = parse(grid)
    assert sheet.errors == []
    assert sheet.rows[0].row_number == 4


def test_identity_headers_are_matched_loosely():
    header = ["Enrolment Number", "Name of Student", "Father's Name", "Mobile No.", "DBMS"]
    sheet = parse([header, [*ID, "Theory=80"]])
    assert sheet.errors == []
    assert sheet.rows[0].parent_name == "Mehul Shah"


def test_plain_value_columns_are_ignored_and_listed():
    header = ["Sr No", *HEADER[:4], "DBMS", "Remarks"]
    sheet = parse([header, ["1", *ID, "Theory=80", "good"]])
    assert sheet.subjects == ["DBMS"]
    assert sheet.ignored_columns == ["Sr No", "Remarks"]


def test_a_subject_column_with_no_data_yet_is_kept():
    sheet = parse([[*HEADER[:4], "DBMS", "Maths"], [*ID, "Theory=80", ""]])
    assert sheet.subjects == ["DBMS", "Maths"]
    assert sheet.rows[0].cells["Maths"].is_empty


def test_bad_cells_are_listed_with_row_and_subject():
    rows = [[*ID, "Theory=120", "Marks=25"]]
    sheet = parse(sheet_rows(rows=rows))
    assert sheet.errors == [
        "Row 2, DBMS: Theory must be a percentage from 0 to 100, like Theory=82",
        "Row 2, OS: Marks must be from 0 to 20",
    ]
    assert sheet.rows == []


def test_missing_and_duplicate_identities():
    rows = [
        [*ID, "", ""],
        ["", "Riya Patel", "Kiran Patel", "9000000102", "", ""],
        ["23ce001", "Avi S", "Mehul Shah", "9000000101", "", ""],
        ["23CE003", "", "Kiran Patel", "9000000102", "", ""],
    ]
    assert parse(sheet_rows(rows=rows)).errors == [
        "Row 3: Enrollment No is missing",
        "Row 4: Enrollment No 23ce001 is also in row 2",
        "Row 5: Student Name is missing",
    ]


def test_invalid_phone_is_a_warning_not_an_error():
    sheet = parse(sheet_rows(rows=[["23CE001", "Avi Shah", "Mehul Shah", "12345", "", ""]]))
    assert sheet.errors == []
    assert sheet.rows[0].phone_e164 is None
    assert sheet.warnings == [
        'Row 2: parent phone is "12345", not a 10-digit mobile number. '
        "This parent cannot be messaged until it is fixed"
    ]


@pytest.mark.parametrize(
    ("grid", "message"),
    [
        ([["Name", "DBMS"], ["Avi", "Theory=80"]], "No header row was found"),
        ([["Enrollment No", "Student Name", "DBMS"], ["1", "Avi", ""]], "no Parent Name column"),
        ([HEADER[:4], ID], "No subject columns were found"),
        ([HEADER], "The sheet has no student rows under the header"),
        ([[*HEADER[:4], "DBMS", "dbms"], [*ID, "", ""]], "Two columns are named dbms"),
    ],
)
def test_sheet_level_problems(grid, message):
    assert any(message in error for error in parse(grid).errors)


def test_over_long_identity_values_are_refused():
    rows = [["2" * 31, "Avi Shah", "Mehul Shah", "9000000101", "", ""]]
    assert parse(sheet_rows(rows=rows)).errors == [
        "Row 2: Enrollment No is longer than 30 characters"
    ]


def test_line_breaks_in_names_become_spaces():
    rows = [["23CE001", "Avi\nShah", "Mehul  Shah", "9000000101", "", ""]]
    row = parse(sheet_rows(rows=rows)).rows[0]
    assert (row.full_name, row.parent_name) == ("Avi Shah", "Mehul Shah")


def test_error_list_is_capped():
    rows = [[f"23CE{n:03}", "Avi", "Mehul", "9000000101", "Theory=120", ""] for n in range(250)]
    errors = parse(sheet_rows(rows=rows)).errors
    assert len(errors) == 201
    assert errors[-1] == "And 50 more problems. Fix these first, then upload again"
