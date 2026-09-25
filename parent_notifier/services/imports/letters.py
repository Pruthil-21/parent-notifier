"""Reading the GIS attendance letters: one page per student, as the college prints them.

Nothing is guessed. Each page is read exactly and checked, or refused with its page
number and the reason; a refused page is never partly used.

- Only a PDF made by a computer can be read: a page without a text layer (a scan) is
  refused. A PDF that needs a password is refused. Doubled "fake bold" characters are
  merged, ligatures expanded and text normalised (NFKC). The Gujarati text lies outside
  every field read.
- Fields are found by the letter's printed labels, not fixed positions: "Outward No:",
  "Regarding Attendance Report of NAME (ENROLLMENT)", "Your son/daughter", "academic
  year 2026-27, Odd term", "from 07-07-26 to 18-09-26", the table's column headings and
  the "Prof." line under the table.
- The table is read twice: by its ruled cells, and by where each word sits under the
  column headings and between the table's own drawn row edges. Both readings must agree
  cell for cell. Every word in the table must belong to exactly one cell, so nothing is
  dropped or counted twice. Each page is measured on its own, so letters with any number
  of subjects, with text at the top, middle or bottom of a cell, and wrapped onto several
  lines all read the same way. A table without lines is read only when every cell starts
  level with its row number; otherwise it is refused, never guessed at.
- On each page the enrollment in the Subject line must equal the one ending the Outward
  No, rows run 1, 2, 3... with no gaps, and every figure must be exactly a percentage
  from 0 to 100, "-", or Mid-Sem marks like 17/20.
"""

import io
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from itertools import pairwise

MAX_PAGES = 100
_UNREADABLE = "The file could not be read as a PDF. Download it from GIS again and retry"

# Column headings, left to right, each found by its first word.
_COLUMNS = ("no", "code", "name", "theory", "practical", "marks", "status")
_HEADING_WORDS = {
    "no", "no.", "sr", "sr.", "subject", "code", "name", "theory", "practical", "(%)", "%",
    "mid", "semester", "sem", "marks", "term", "work", "status",
}  # fmt: skip
# A value may start this far left of its heading; cells share the heading's padding.
_ALIGN = 3.0
# Words whose tops are this close sit on the same line.
_SAME_LINE = 2.0

_OUTWARD = re.compile(
    r"Outward\s*No\s*[:.]?\s*[A-Z]+\s*/\s*(\d{4}-\d{2})\s*/\s*(Odd|Even)\s*/\s*[A-Za-z]+\s*/\s*"
    r"(\d{6,20})\s*/?",
    re.IGNORECASE,
)
_SUBJECT = re.compile(r"Attendance\s+Report\s+of\s+(.+?)\s*\(\s*(\d{6,20})\s*\)", re.IGNORECASE)
_CHILD = re.compile(r"\bYour\s+(son|daughter)\b", re.IGNORECASE)
_YEAR_TERM = re.compile(r"academic\s+year\s+(\d{4}-\d{2})\s*,?\s*(Odd|Even)\s+term", re.IGNORECASE)
_PERIOD = re.compile(
    r"\bfrom\s+(\d{2}-\d{2}-\d{2,4})\s+to\s+(\d{2}-\d{2}-\d{2,4})\b", re.IGNORECASE
)
_ROW_NUMBER = re.compile(r"^\d{1,2}$")
_CODE = re.compile(r"^[A-Z0-9]{4,15}$")
_PERCENT = re.compile(r"^(\d{1,3}(?:\.\d{1,2})?)$")
_MARKS = re.compile(r"^(\d{1,3}(?:\.\d{1,2})?)\s*/\s*(\d{1,3})$")
_NONE = {"-", "--", "–", ""}  # noqa: RUF001  (a hyphen, two, an en dash, or nothing)
_ABSENT = {"ab", "abs", "absent"}
_STATUS = re.compile(r"^[A-Za-z .()/-]{0,40}$")


_NOT_LEVEL = (
    "its table has no lines and its text is not level with the row numbers, so the rows "
    "cannot be told apart safely"
)


class LetterFileError(ValueError):
    """The whole file cannot be read; the message says what to do instead."""


@dataclass(frozen=True)
class LetterSubject:
    code: str
    name: str
    theory: float | None
    practical: float | None
    marks: float | None
    absent: bool
    out_of: int | None  # the total written with the marks, like 20 in 17/20


@dataclass(frozen=True)
class Letter:
    page: int
    enrollment: str
    student_name: str
    parent_name: str
    gender: str | None
    year: str
    term: str  # "Odd" or "Even"
    attendance_from: date
    attendance_to: date
    mentor: str
    subjects: tuple[LetterSubject, ...]


@dataclass
class LetterFile:
    pages: int
    letters: list[Letter]
    problems: list[str]  # one or more per refused page


class _PageError(Exception):
    """This page cannot be used; the message says why."""


def _clean(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text or "").split())


def _day(text: str) -> date:
    day, month, year = (int(part) for part in text.split("-"))
    return date(2000 + year if year < 100 else year, month, day)


def _lines(words: list[dict]) -> list[list[dict]]:
    """Words grouped into lines, top to bottom, each line left to right."""
    lines: list[list[dict]] = []
    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if lines and abs(lines[-1][0]["top"] - word["top"]) <= _SAME_LINE:
            lines[-1].append(word)
        else:
            lines.append([word])
    return [sorted(line, key=lambda w: w["x0"]) for line in lines]


def _heading(words: list[dict]) -> tuple[list[float], float, float]:
    """The left edge of each column, and the top and bottom of the heading rows."""
    lines = _lines(words)

    def heading_line(line) -> bool:
        return all(w["text"].lower() in _HEADING_WORDS for w in line)

    def block(anchor: int) -> list[dict]:
        """The run of heading-only lines around a line, as headings wrap onto several
        lines and a short one may sit lower when its cell centres it."""
        start = anchor
        while start > 0 and heading_line(lines[start - 1]):
            start -= 1
        end = anchor
        while end + 1 < len(lines) and heading_line(lines[end + 1]):
            end += 1
        return [w for line in lines[start : end + 1] for w in line]

    band = next(
        (
            found
            for index, line in enumerate(lines)
            if heading_line(line) and "theory" in {w["text"].lower() for w in line}
            for found in [block(index)]
            if "practical" in {w["text"].lower() for w in found}
        ),
        None,
    )
    if band is None:
        raise _PageError("the table's column headings were not found")

    def first(*names) -> list[float]:
        return sorted(w["x0"] for w in band if w["text"].lower() in names)

    subjects = first("subject")
    found = {
        "no": first("no", "no.", "sr", "sr."),
        "theory": first("theory"),
        "practical": first("practical"),
        "marks": first("mid"),
        "status": first("term"),
    }
    if len(subjects) != 2 or not all(found.values()):
        raise _PageError("the table's column headings were not all found")
    lefts = [
        found["no"][0],
        subjects[0],
        subjects[1],
        found["theory"][0],
        found["practical"][0],
        found["marks"][0],
        found["status"][0],
    ]
    if lefts != sorted(lefts) or len(set(lefts)) != len(lefts):
        raise _PageError("the table's columns are not in the expected order")
    top = min(w["top"] for w in band)
    return [left - _ALIGN for left in lefts], top, max(w["bottom"] for w in band)


def _column(x0: float, lefts: list[float]) -> int | None:
    if x0 < lefts[0]:
        return None
    return max(index for index, left in enumerate(lefts) if x0 >= left)


def _row_edges(page, lefts, top: float, bottom: float) -> list[float]:
    """The height of each ruled edge across this page's table, top to bottom, from its
    lines or its cell boxes. Edges drawn a hair apart, as double lines or the sides of two
    boxes, count as one. Tables with any number of rows are measured the same way."""
    spans: dict[float, list[float]] = {}
    for edge in page.horizontal_edges:
        if top <= edge["top"] <= bottom:
            key = next((y for y in spans if abs(y - edge["top"]) <= 1.5), edge["top"])
            spans.setdefault(key, [edge["x0"], edge["x1"]])
            spans[key] = [min(spans[key][0], edge["x0"]), max(spans[key][1], edge["x1"])]
    # Only edges running across the table, from its first columns to its last ones.
    return sorted(y for y, (x0, x1) in spans.items() if x0 <= lefts[1] and x1 >= lefts[5])


def _centre(word: dict) -> float:
    return (word["top"] + word["bottom"]) / 2


def _row_of(word, anchors, edges) -> int | None:
    """The row a word belongs to. With ruled edges, the row between the edges around it,
    however the text sits in its cell. Without them the text must sit level with its row
    number, which the caller checks."""
    if edges:
        for upper, lower in pairwise(edges):
            if upper < _centre(word) < lower:
                inside = [i for i, a in enumerate(anchors) if upper < _centre(a) < lower]
                return inside[0] if len(inside) == 1 else None
        return None
    return max(
        (i for i, anchor in enumerate(anchors) if word["top"] >= anchor["top"] - _SAME_LINE),
        default=None,
    )


def _edges_fit(edges, anchors) -> bool:
    """Ruled edges are used only when they give every row number a row of its own."""
    between = list(pairwise(edges))
    counts = [sum(upper < _centre(a) < lower for a in anchors) for upper, lower in between]
    return sum(counts) == len(anchors) and all(count <= 1 for count in counts)


def _rows_by_position(page, words, lefts, heading_bottom) -> tuple[list[list[str]], float]:
    """The table's cells from where each word sits, and the top of the "Prof." line."""
    below = [w for w in words if w["top"] > heading_bottom]
    prof = min(
        (w for w in below if w["text"].lower().startswith("prof") and w["x0"] < lefts[2]),
        key=lambda w: w["top"],
        default=None,
    )
    if prof is None:
        raise _PageError('the mentor\'s "Prof." line under the table was not found')
    body = [w for w in below if w["top"] < prof["top"] - _SAME_LINE]
    anchors = sorted(
        (w for w in body if _column(w["x0"], lefts) == 0 and _ROW_NUMBER.match(w["text"])),
        key=lambda w: w["top"],
    )
    if not anchors:
        raise _PageError("the table has no subject rows")
    edges = _row_edges(page, lefts, heading_bottom - 4, prof["top"])
    if not _edges_fit(edges, anchors):
        edges = []
    rows: list[list[list[dict]]] = [[[] for _ in _COLUMNS] for _ in anchors]
    for word in body:
        column = _column(word["x0"], lefts)
        row = _row_of(word, anchors, edges)
        if row is None and column is not None and not edges:
            raise _PageError(_NOT_LEVEL)
        if column is None or row is None:
            raise _PageError(f'"{word["text"]}" sits outside the table\'s rows and columns')
        rows[row][column].append(word)
    if not edges:
        # Without lines, a cell that starts away from its row number could belong to the
        # row above or below, so such a table is refused rather than guessed at.
        for anchor, row in zip(anchors, rows, strict=True):
            tops = [min(w["top"] for w in cell) for cell in row if cell]
            if any(abs(top - anchor["top"]) > _SAME_LINE for top in tops):
                raise _PageError(_NOT_LEVEL)
    cells = [
        [_clean(" ".join(w["text"] for line in _lines(cell) for w in line)) for cell in row]
        for row in rows
    ]
    return cells, prof["top"]


def _rows_by_ruling(page, top: float, bottom: float) -> list[list[str]] | None:
    """The table's cells from its ruled lines, or None when it has none. Only the band
    from the headings to the "Prof." line is searched, which is much quicker."""
    band = page.crop((0, max(0, top), page.width, min(page.height, bottom)), strict=False)
    for table in band.find_tables({"vertical_strategy": "lines", "horizontal_strategy": "lines"}):
        rows = [[_clean(cell or "") for cell in row] for row in table.extract()]
        heading = " ".join(rows[0]).lower() if rows else ""
        if "subject" in heading and "theory" in heading:
            return [row for row in rows[1:] if any(row)]
    return None


def _percent(text: str, label: str) -> float | None:
    if text in _NONE:
        return None
    match = _PERCENT.match(text)
    if match is None or float(match[1]) > 100:
        raise _PageError(f'{label} "{text}" is not a percentage from 0 to 100')
    return float(match[1])


def _marks(text: str) -> tuple[float | None, bool, int | None]:
    if text in _NONE:
        return None, False, None
    if text.lower() in _ABSENT:
        return None, True, None
    match = _MARKS.match(text)
    if match is None:
        raise _PageError(f'Mid-Sem marks "{text}" are not like 17/20')
    marks, total = float(match[1]), int(match[2])
    if not 1 <= total <= 100 or marks > total:
        raise _PageError(f'Mid-Sem marks "{text}" are more than the total')
    return marks, False, total


def _subjects(cells: list[list[str]]) -> tuple[LetterSubject, ...]:
    subjects = []
    for expected, row in enumerate(cells, start=1):
        number, code, name, theory, practical, marks, status = row
        if number != str(expected):
            raise _PageError(f"the table's rows are not numbered 1, 2, 3... (row {expected})")
        if not _CODE.match(code):
            raise _PageError(f'row {expected} has subject code "{code}"')
        if not name:
            raise _PageError(f"row {expected} has no subject name")
        if not _STATUS.match(status):
            raise _PageError(f'row {expected} has term work status "{status}"')
        mid, absent, total = _marks(marks)
        subjects.append(
            LetterSubject(
                code,
                name,
                _percent(theory, f"Row {expected} Theory"),
                _percent(practical, f"Row {expected} Practical"),
                mid,
                absent,
                total,
            )
        )
    codes = [subject.code for subject in subjects]
    if len(set(codes)) != len(codes):
        raise _PageError("a subject code appears twice in the table")
    return tuple(subjects)


def _parent(text: str) -> str:
    """The first line after "To,", the parent's name; empty if it looks like an address."""
    lines = [_clean(line) for line in text.splitlines()]
    for index, line in enumerate(lines[:-1]):
        if line.lower().rstrip(",") == "to":
            name = lines[index + 1].rstrip(",").strip()
            return "" if re.search(r"\d", name) else name[:120]
    return ""


def _mentor(words, prof_top) -> str:
    line = [w for w in words if abs(w["top"] - prof_top) <= _SAME_LINE]
    return _clean(" ".join(w["text"] for w in sorted(line, key=lambda w: w["x0"])))[:120]


def _read_page(page, number: int) -> Letter:
    page = page.dedupe_chars(tolerance=1)
    if not page.chars:
        raise _PageError("it has no text to read, so it may be a scan")
    words = [
        {**word, "text": _clean(word["text"])}
        for word in page.extract_words(expand_ligatures=True)
        if _clean(word["text"])
    ]
    raw_text = page.extract_text() or ""
    text = _clean(raw_text)

    outward = _OUTWARD.search(text)
    subject = _SUBJECT.search(text)
    year_term = _YEAR_TERM.search(text)
    period = _PERIOD.search(text)
    if outward is None:
        raise _PageError('its "Outward No" was not found')
    if subject is None:
        raise _PageError('its "Regarding Attendance Report of" line was not found')
    if outward[3] != subject[2]:
        raise _PageError(
            f"the enrollment in its Subject line ({subject[2]}) differs from the one in its "
            f"Outward No ({outward[3]})"
        )
    if year_term is None or period is None:
        raise _PageError("its academic year, term or attendance dates were not found")
    if (year_term[1], year_term[2].lower()) != (outward[1], outward[2].lower()):
        raise _PageError("its academic year or term differs between the Outward No and the text")
    try:
        start, end = _day(period[1]), _day(period[2])
    except ValueError:
        raise _PageError(
            f"its attendance dates {period[1]} to {period[2]} are not real dates"
        ) from None
    if start > end:
        raise _PageError("its attendance period ends before it starts")
    children = {match.lower() for match in _CHILD.findall(text)}

    lefts, heading_top, heading_bottom = _heading(words)
    cells, prof_top = _rows_by_position(page, words, lefts, heading_bottom)
    # A little above the headings, so the table's top line is inside the band.
    ruled = _rows_by_ruling(page, heading_top - 8, prof_top - 1)
    if ruled is not None and ruled != cells:
        raise _PageError("its table reads differently by its lines and by its text")
    return Letter(
        page=number,
        enrollment=subject[2],
        student_name=_clean(subject[1])[:120],
        parent_name=_parent(raw_text),
        gender={"son": "male", "daughter": "female"}[children.pop()]
        if len(children) == 1
        else None,
        year=outward[1],
        term=outward[2].capitalize(),
        attendance_from=start,
        attendance_to=end,
        mentor=_mentor(words, prof_top),
        subjects=_subjects(cells),
    )


def read_letters(data: bytes) -> LetterFile:
    """Every page of the PDF, read or refused. Nothing is written anywhere."""
    import pdfplumber
    from pdfminer.pdfdocument import PDFPasswordIncorrect

    try:
        pdf = pdfplumber.open(io.BytesIO(data))
        pages = list(pdf.pages)
    # pdfminer raises many kinds of error for a damaged or locked file.
    except Exception as error:
        # pdfplumber wraps pdfminer's error as its first argument.
        inner = error.args[0] if error.args else None
        if isinstance(error, PDFPasswordIncorrect) or isinstance(inner, PDFPasswordIncorrect):
            raise LetterFileError(
                "This PDF is locked with a password. Download it from GIS again without one"
            ) from None
        raise LetterFileError(_UNREADABLE) from None
    with pdf:
        if not pages:
            raise LetterFileError("The PDF has no pages")
        if len(pages) > MAX_PAGES:
            raise LetterFileError(f"The PDF has more than {MAX_PAGES} pages. Upload one class")
        letters, problems = [], []
        for number, page in enumerate(pages, start=1):
            try:
                letters.append(_read_page(page, number))
            except _PageError as refused:
                problems.append(f"Page {number}: {refused}")
            # A page pdfminer cannot lay out is refused like any other unreadable page.
            except Exception:
                problems.append(f"Page {number}: it could not be read")
        return LetterFile(len(pages), letters, problems)
