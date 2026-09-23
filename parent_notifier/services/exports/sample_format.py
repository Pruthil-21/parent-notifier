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


def sample_format() -> bytes:
    workbook, sheet = new_sheet("Sheet format", IDENTITY_HEADERS + EXAMPLE_SUBJECTS)
    add_row(sheet, EXAMPLE_ROW)
    return to_bytes(workbook)
