"""Turning the read letters into a sheet for the review page, with the checks that need
the whole PDF, the semester and the class.

Blocking problems: a refused page; letters from more than one year and term, attendance
period or mentor; a subject code with two names or two Mid-Sem totals; a student on two
pages; an Odd-term PDF uploaded into an even semester (or the other way round); and a
student whose name in the letter shares no word with the name the class holds for that
enrollment, which points to a wrong enrollment number.

Warnings: students not yet on the class list (added without a phone), class-list
students with no letter, names that share only one word, and letters signed by someone
other than the signed-in mentor.
"""

import re
from collections import defaultdict

from parent_notifier.models.academics import Student
from parent_notifier.services.imports.cell_parser import SubjectCell
from parent_notifier.services.imports.letters import Letter, LetterFile
from parent_notifier.services.imports.sheet_parser import ParsedSheet, SheetRow

_SMALL_WORDS = {"a", "an", "and", "as", "at", "by", "for", "in", "of", "on", "or", "the", "to"}
_ROMAN = re.compile(r"^[IVX]+$")
MAX_LISTED = 10


def title_case(text: str) -> str:
    """ "DATA STRUCTURES" as "Data Structures" and "PATEL RIYA" as "Patel Riya". Text
    already in mixed case is kept; Roman numerals such as II stay capitals."""
    if text != text.upper():
        return text
    words = []
    for index, word in enumerate(text.split()):
        lower = word.lower()
        if _ROMAN.match(word):
            words.append(word)
        elif index and lower in _SMALL_WORDS:
            words.append(lower)
        else:
            words.append("-".join(part[:1].upper() + part[1:] for part in lower.split("-")))
    return " ".join(words)


def _students(count: int, verb: str) -> str:
    """ "1 student is" or "3 students are", and the same for "has"/"have"."""
    plural = {"is": "are", "has": "have"}[verb]
    return f"1 student {verb}" if count == 1 else f"{count} students {plural}"


def _words(name: str) -> set[str]:
    return {word for word in re.findall(r"[a-z]+", name.lower()) if len(word) > 1}


def _pages(letters: list[Letter]) -> str:
    numbers = [str(letter.page) for letter in letters]
    shown = ", ".join(numbers[:MAX_LISTED])
    return shown + (f" and {len(numbers) - MAX_LISTED} more" if len(numbers) > MAX_LISTED else "")


def _one_of_each(letters: list[Letter], sheet: ParsedSheet) -> None:
    for label, key in (
        ("academic year and term", lambda letter: (letter.year, letter.term)),
        ("attendance period", lambda letter: (letter.attendance_from, letter.attendance_to)),
        ("mentor", lambda letter: letter.mentor.lower()),
    ):
        groups = defaultdict(list)
        for letter in letters:
            groups[key(letter)].append(letter)
        if len(groups) > 1:
            parts = "; ".join(f"pages {_pages(group)}" for group in groups.values())
            sheet.errors.append(
                f"The letters do not all have the same {label} ({parts}). Upload one class's "
                "letters for one term"
            )


def _subject_names(letters: list[Letter], sheet: ParsedSheet) -> tuple[dict, dict]:
    """Each subject code's name for the class, in the order the letters list them, and its
    Mid-Sem total where one is written."""
    names: dict[str, set[str]] = defaultdict(set)
    totals: dict[str, set[int]] = defaultdict(set)
    for letter in letters:
        for subject in letter.subjects:
            names[subject.code].add(subject.name)
            if subject.out_of is not None:
                totals[subject.code].add(subject.out_of)
    shown = {}
    for code, found in names.items():
        if len(found) > 1:
            sheet.errors.append(
                f"Subject {code} has different names on different pages: {', '.join(sorted(found))}"
            )
        shown[code] = title_case(sorted(found)[0])
        if len(totals[code]) > 1:
            listed = " and ".join(str(total) for total in sorted(totals[code]))
            sheet.errors.append(f"{shown[code]} ({code}) has Mid-Sem marks out of {listed}")
    duplicates = [name for name in set(shown.values()) if list(shown.values()).count(name) > 1]
    for name in duplicates:
        sheet.errors.append(f"Two subject codes are both named {name}")
    return shown, {code: next(iter(found)) for code, found in totals.items() if len(found) == 1}


def _against_class(sheet: ParsedSheet, stored: dict[str, Student]) -> None:
    new_pages = []
    for row in sheet.rows:
        student = stored.get(row.enrollment_no.upper())
        if student is None:
            new_pages.append(str(row.row_number))
            continue
        shared = len(_words(row.full_name) & _words(student.full_name))
        fewest = min(len(_words(row.full_name)), len(_words(student.full_name)))
        if shared == 0:
            sheet.errors.append(
                f"Page {row.row_number}: {row.full_name} ({row.enrollment_no}) does not match "
                f"{student.full_name}, who has that enrollment in the class list. Check the "
                "enrollment numbers before importing"
            )
        elif shared == 1 and fewest > 1:
            sheet.warnings.append(
                f"Page {row.row_number}: check that {row.full_name} is {student.full_name}; "
                "the names share only one word"
            )
    if new_pages:
        pages = ", ".join(new_pages[:MAX_LISTED]) + (
            " and more" if len(new_pages) > MAX_LISTED else ""
        )
        sheet.warnings.append(
            f"{_students(len(new_pages), 'is')} not on the class list "
            f"({'page' if len(new_pages) == 1 else 'pages'} {pages}). "
            "They will be added without a parent phone, so their parents cannot be messaged "
            "until a phone is added"
        )
    in_pdf = {row.enrollment_no.upper() for row in sheet.rows}
    missing = [
        student.full_name
        for key, student in stored.items()
        if key not in in_pdf and student.status == "active"
    ]
    if missing:
        listed = ", ".join(sorted(missing)[:MAX_LISTED])
        more = f" and {len(missing) - MAX_LISTED} more" if len(missing) > MAX_LISTED else ""
        sheet.warnings.append(
            f"{_students(len(missing), 'has')} no letter in this PDF though on the class list: "
            f"{listed}{more}"
        )


def to_sheet(
    file: LetterFile,
    semester_number: int,
    class_max: int,
    stored: dict[str, Student],
    mentor_name: str,
) -> ParsedSheet:
    sheet = ParsedSheet(source="pdf")
    sheet.errors.extend(file.problems)
    letters = file.letters
    if not letters:
        if not sheet.errors:
            sheet.errors.append("No letters were found in the PDF")
        return sheet
    _one_of_each(letters, sheet)
    by_enrollment = defaultdict(list)
    for letter in letters:
        by_enrollment[letter.enrollment.upper()].append(letter)
    for enrollment, found in by_enrollment.items():
        if len(found) > 1:
            sheet.errors.append(f"Enrollment {enrollment} has a letter on pages {_pages(found)}")
    term = letters[0].term
    if (term == "Odd") != (semester_number % 2 == 1):
        kind = "odd" if semester_number % 2 else "even"
        sheet.errors.append(
            f"The letters are for the {term} term, but Sem {semester_number} is an {kind} "
            f"semester. Upload them into the right semester"
        )
    names, totals = _subject_names(letters, sheet)
    sheet.subjects = list(names.values())
    sheet.subject_max = {names[code]: total for code, total in totals.items()}
    for letter in letters:
        cells = {
            names[s.code]: SubjectCell(
                s.theory,
                s.practical,
                s.marks,
                s.absent,
                None if s.out_of == class_max else s.out_of,
            )
            for s in letter.subjects
        }
        sheet.rows.append(
            SheetRow(
                letter.page,
                letter.enrollment,
                title_case(letter.student_name),
                title_case(letter.parent_name),
                "",
                None,
                {name: cells.get(name, SubjectCell()) for name in sheet.subjects},
                letter.gender,
            )
        )
        if letter.gender is None:
            sheet.warnings.append(
                f"Page {letter.page}: the letter does not say son or daughter, so the message "
                "will say your ward"
            )
    first = letters[0]
    sheet.attendance_from = first.attendance_from.isoformat()
    sheet.attendance_to = first.attendance_to.isoformat()
    sheet.letter_info = {
        "pages": file.pages,
        "read": len(letters),
        "term": f"{first.year}, {first.term} term",
        "mentor": first.mentor,
    }
    if not (_words(first.mentor) & _words(mentor_name)):
        sheet.warnings.append(f"The letters are signed by {first.mentor}, not by you")
    _against_class(sheet, stored)
    # Problems for the whole PDF first, then each page's in page order.
    sheet.errors.sort(key=_page_order)
    sheet.warnings.sort(key=_page_order)
    return sheet


def _page_order(problem: str) -> int:
    found = re.match(r"Page (\d+):", problem)
    return int(found[1]) if found else 0
