"""Turning a grid of strings into students and subject results, with every problem listed.

The header row is found in the first few rows, identity columns are matched loosely by
name, and every other column is a subject when its cells look like "Theory=86". Columns
of plain values, such as "Sr No", are ignored and listed.
"""

import re
from dataclasses import dataclass, field

from parent_notifier.services.imports.cell_parser import CellError, SubjectCell, parse_cell
from parent_notifier.services.shared.phone import normalise_indian_mobile

HEADER_SEARCH_ROWS = 10
MAX_ERRORS = 200
# Longest value each identity column holds in the database.
IDENTITY_LIMITS = {"enrollment_no": 30, "full_name": 120, "parent_name": 120, "phone": 40}
IDENTITY_LABELS = {
    "enrollment_no": "Enrollment No",
    "full_name": "Student Name",
    "parent_name": "Parent Name",
    "phone": "Parent Phone",
}
# Header names accepted for each identity column, after _normalise().
_ALIASES = {
    key: set(names.split("|"))
    for key, names in {
        "enrollment_no": "enrollment no|enrolment no|enrollment|enrolment|enroll no|en no"
        "|enrollment id",
        "full_name": "student name|name|name of student|student|full name",
        "parent_name": "parent name|parents name|parent|father name|fathers name"
        "|guardian name|mother name",
        "phone": "parent phone|parents phone|parent mobile|parents mobile|phone|mobile"
        "|mobile no|phone no|contact|contact no|whatsapp|parent contact|parent whatsapp"
        "|parent phone no|parent mobile no",
        "gender": "gender|sex|son daughter|son or daughter|boy girl|boy or girl",
    }.items()
}
# Son or daughter, however it is written; the message says "your son" or "your daughter".
_GENDERS = {
    **dict.fromkeys(("son", "male", "m", "boy"), "male"),
    **dict.fromkeys(("daughter", "female", "f", "girl"), "female"),
}
# A number Excel wrote in scientific form, like 1.25020405011E+13, has already lost its
# last digits, so it can never be matched or messaged.
_SHORTENED = re.compile(r"^\d(?:\.\d+)?e\+?\d+$", re.IGNORECASE)
MAX_SUBJECT_NAME = 80


@dataclass(frozen=True)
class SheetRow:
    row_number: int
    enrollment_no: str
    full_name: str
    parent_name: str
    phone_raw: str
    phone_e164: str | None
    cells: dict[str, SubjectCell]
    gender: str | None = None  # None when the sheet does not say


@dataclass
class ParsedSheet:
    subjects: list[str] = field(default_factory=list)
    rows: list[SheetRow] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    ignored_columns: list[str] = field(default_factory=list)
    # The days the attendance covers, as ISO dates ("2026-07-07"), when known.
    attendance_from: str | None = None
    attendance_to: str | None = None
    # Each subject with Mid-Sem marks and the total they are out of.
    subject_max: dict[str, int] = field(default_factory=dict)
    # Staged while creating its class: cancelling the review removes that class again.
    new_class: bool = False
    # "sheet" or "pdf". Letters never change a saved student's details; they only fill
    # in what is missing, since GIS writes names differently from the class list.
    source: str = "sheet"
    # For a PDF: its pages, how many were read, the term and who signed the letters.
    letter_info: dict = field(default_factory=dict)

    @property
    def is_class_list(self) -> bool:
        """Students and contacts only, with no subjects: a class's base list."""
        return not self.subjects


def _normalise(header: str) -> str:
    # "Father's" and "Fathers" are the same header.
    words = re.sub(r"[^a-z0-9]+", " ", re.sub(r"['\u2019]", "", header.lower())).split()
    return " ".join("no" if word in {"number", "num"} else word for word in words)


def _identity_columns(header: list[str]) -> dict[str, int]:
    found: dict[str, int] = {}
    for index, title in enumerate(header):
        for key, aliases in _ALIASES.items():
            if key not in found and _normalise(title) in aliases:
                found[key] = index
                break
    return found


def _find_header(grid: list[list[str]]) -> tuple[int, dict[str, int]] | None:
    for index, row in enumerate(grid[:HEADER_SEARCH_ROWS]):
        columns = _identity_columns(row)
        if {"enrollment_no", "full_name"} <= columns.keys():
            return index, columns
    return None


def _looks_like_subject(values: list[str]) -> bool:
    filled = [value for value in values if value]
    return not filled or any("=" in value or ":" in value for value in filled)


def _columns(grid, header_index, identity, sheet: ParsedSheet) -> dict[str, int]:
    header = grid[header_index]
    subjects: dict[str, int] = {}
    for index, title in enumerate(header):
        if index in identity.values() or not title:
            continue
        values = [row[index] if index < len(row) else "" for row in grid[header_index + 1 :]]
        if not _looks_like_subject(values):
            sheet.ignored_columns.append(title)
        elif len(title) > MAX_SUBJECT_NAME:
            sheet.errors.append(
                f"Subject {title[:30]}... is longer than {MAX_SUBJECT_NAME} characters"
            )
        elif title.lower() in (name.lower() for name in subjects):
            sheet.errors.append(f"Two columns are named {title}. Give each subject its own name")
        else:
            subjects[title] = index
    return subjects


def _identity_problems(number: int, values: dict[str, str]) -> list[str]:
    problems = [
        f"Row {number}: {IDENTITY_LABELS[key]} is missing"
        for key in ("enrollment_no", "full_name")
        if not values[key]
    ]
    problems += [
        f"Row {number}: {IDENTITY_LABELS[key]} is longer than {limit} characters"
        for key, limit in IDENTITY_LIMITS.items()
        if len(values[key]) > limit
    ]
    return problems


def _row(number, cells, identity, subjects, midsem_max, sheet: ParsedSheet) -> SheetRow | None:
    def value(key):
        index = identity.get(key)
        # Line breaks typed inside a cell become single spaces.
        return " ".join(cells[index].split()) if index is not None and index < len(cells) else ""

    enrollment, name, phone = value("enrollment_no"), value("full_name"), value("phone")
    problems = _identity_problems(number, {key: value(key) for key in IDENTITY_LIMITS})
    for key, raw in (("enrollment_no", enrollment), ("phone", phone)):
        if _SHORTENED.match(raw):
            problems.append(
                f"Row {number}: {IDENTITY_LABELS[key]} {raw} was shortened by Excel and has lost "
                "digits. Format the column as Text, type the numbers again and save"
            )
    gender = _GENDERS.get(value("gender").lower())
    if value("gender") and gender is None:
        sheet.warnings.append(
            f'Row {number}: Son or daughter "{value("gender")}" is not Son or Daughter, so it '
            "is left unset"
        )
    parsed: dict[str, SubjectCell] = {}
    for subject, index in subjects.items():
        try:
            parsed[subject] = parse_cell(cells[index] if index < len(cells) else "", midsem_max)
        except CellError as error:
            problems.append(f"Row {number}, {subject}: {error}")
    sheet.errors.extend(problems)
    phone_e164 = normalise_indian_mobile(phone)
    if phone_e164 is None and not _SHORTENED.match(phone):
        shown = f'"{phone}"' if phone else "blank"
        sheet.warnings.append(
            f"Row {number}: parent phone is {shown}, not a 10-digit mobile number. "
            "This parent cannot be messaged until it is fixed"
        )
    if problems:
        return None
    return SheetRow(
        number, enrollment, name, value("parent_name"), phone, phone_e164, parsed, gender
    )


def _subject_totals(sheet: ParsedSheet, midsem_max: int) -> None:
    """One total per subject: marks written as 18/25 make it out of 25, plain marks are
    out of the class's total, and a subject cannot mix the two."""
    for subject in sheet.subjects:
        totals = {
            row.cells[subject].out_of or midsem_max
            for row in sheet.rows
            if row.cells[subject].marks is not None
        }
        if len(totals) > 1:
            listed = " and ".join(str(total) for total in sorted(totals))
            sheet.errors.append(
                f"{subject}: Mid-Sem marks are out of {listed} in different rows. Write every "
                "mark in the subject out of the same total, like 18/25"
            )
        elif totals:
            sheet.subject_max[subject] = totals.pop()


def parse_sheet(grid: list[list[str]], midsem_max: int, class_list: bool = False) -> ParsedSheet:
    """`class_list` accepts a sheet with no subject columns: the students of a new class."""
    sheet = ParsedSheet()
    found = _find_header(grid)
    if found is None:
        sheet.errors.append(
            "No header row was found. The first columns must be Enrollment No, "
            "Student Name, Parent Name and Parent Phone"
        )
        return sheet
    header_index, identity = found
    for key in ("parent_name", "phone"):
        if key not in identity:
            sheet.errors.append(f"The sheet has no {IDENTITY_LABELS[key]} column")
    subjects = _columns(grid, header_index, identity, sheet)
    sheet.subjects = list(subjects)
    if not subjects and not class_list:
        sheet.errors.append("No subject columns were found. Each subject needs its own column")
    seen: dict[str, int] = {}
    for offset, cells in enumerate(grid[header_index + 1 :], start=header_index + 2):
        if not any(cells):
            continue
        row = _row(offset, cells, identity, subjects, midsem_max, sheet)
        if row is None:
            continue
        key = row.enrollment_no.upper()
        if key in seen:
            sheet.errors.append(
                f"Row {offset}: Enrollment No {row.enrollment_no} is also in row {seen[key]}"
            )
            continue
        seen[key] = offset
        sheet.rows.append(row)
    _subject_totals(sheet, midsem_max)
    if not sheet.rows and not sheet.errors:
        sheet.errors.append("The sheet has no student rows under the header")
    if len(sheet.errors) > MAX_ERRORS:
        hidden = len(sheet.errors) - MAX_ERRORS
        sheet.errors[MAX_ERRORS:] = [
            f"And {hidden} more problems. Fix these first, then upload again"
        ]
    return sheet
