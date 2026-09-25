"""The sheet format: the columns a mentor's sheet needs, with one example row."""

from parent_notifier.services.exports.workbook_style import (
    IDENTITY_HEADERS,
    add_row,
    new_sheet,
    to_bytes,
)

EXAMPLE_SUBJECTS = ["Data Structures", "DBMS", "Mathematics"]
# Fictional example; a theory-only subject and an absent Mid-Sem show those cases.
EXAMPLE_ROW = [
    "230120107001",
    "Student Name",
    "Parent Name",
    "90000 00001",
    "Theory=86,Practical=92,Marks=16",
    "Theory=79,Practical=81,Marks=AB",
    "Theory=91,Marks=14",
]


# Son or daughter is not asked for: the GIS letters PDF brings it.
CLASS_LIST_HEADERS = IDENTITY_HEADERS
# Fictional example students.
CLASS_LIST_ROWS = [
    ["230120107001", "Student Name", "Parent Name", "90000 00001"],
    ["230120107002", "Student Name", "Parent Name", "90000 00002"],
]


def class_list_format() -> bytes:
    """The base class list: who the students are and how to reach their parents."""
    workbook, sheet = new_sheet("Class list", CLASS_LIST_HEADERS)
    for row in CLASS_LIST_ROWS:
        add_row(sheet, row)
    return to_bytes(workbook)


def sample_format() -> bytes:
    workbook, sheet = new_sheet("Sheet format", IDENTITY_HEADERS + EXAMPLE_SUBJECTS)
    add_row(sheet, EXAMPLE_ROW)
    return to_bytes(workbook)
