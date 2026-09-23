"""Sheets built in code. Fictional students only; phones from +91 90000 00101 upward."""

import io

from openpyxl import Workbook

HEADER = ["Enrollment No", "Student Name", "Parent Name", "Parent Phone", "DBMS", "OS"]
ROWS = [
    [
        "23CE001",
        "Avi Shah",
        "Mehul Shah",
        "90000 00101",
        "Theory=86,Practical=92,Marks=16",
        "Theory=79,Marks=AB",
    ],
    [
        "23CE002",
        "Riya Patel",
        "Kiran Patel",
        "90000 00102",
        "Theory=70,Practical=88,Marks=5",
        "Theory=91,Marks=14",
    ],
]


def sheet_rows(header=None, rows=None) -> list[list[object]]:
    return [header or HEADER, *(ROWS if rows is None else rows)]


def make_xlsx(rows: list[list[object]] | None = None) -> bytes:
    workbook = Workbook()
    for row in rows or sheet_rows():
        workbook.active.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def make_csv(rows: list[list[object]] | None = None, encoding: str = "utf-8") -> bytes:
    lines = []
    for row in rows or sheet_rows():
        lines.append(",".join(f'"{value}"' for value in row))
    return ("\r\n".join(lines) + "\r\n").encode(encoding)
