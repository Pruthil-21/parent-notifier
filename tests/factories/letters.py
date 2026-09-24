"""Made-up GIS attendance letters as PDFs, laid out like the college's: one page per
student, a ruled table of subjects, and the letter text around it. Every name and number
here is fictional; real letters are never used in tests."""

import io
from dataclasses import dataclass, field, replace
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, Table, TableStyle

HEADER = ["No", "Subject Code", "Subject Name", "Theory (%)", "Practical (%)",
          "Mid Semester Marks", "Term Work Status"]  # fmt: skip
WIDTHS = [24, 60, 160, 48, 56, 66, 68]
_CELL = ParagraphStyle("cell", fontName="Helvetica", fontSize=7.5, leading=9)
_BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=9, leading=12)


@dataclass(frozen=True)
class Row:
    code: str
    name: str
    theory: str
    practical: str
    marks: str
    status: str = "Satisfactory"


@dataclass(frozen=True)
class Letter:
    enrollment: str = "12502040500001"
    student: str = "PATEL RIYA KIRANBHAI"
    parent: str = "PATEL KIRANBHAI"
    child: str = "daughter"
    rows: tuple[Row, ...] = field(
        default_factory=lambda: (
            Row(
                "102003406",
                "PROBABILITY STATISTICS AND NUMERICAL METHODS",
                "71.88",
                "60.0",
                "20/20",
                "Not Satisfactory",
            ),
            Row("102003407", "Entrepreneurship Skills", "63.64", "-", "18/25", "Not Applicable"),
            Row("102003411", "UNIVERSAL HUMAN VALUES", "46.15", "-", "0/25", "Not Applicable"),
            Row("102040304", "DATA STRUCTURES", "73.08", "77.78", "17/20"),
            Row("102040305", "DATABASE MANAGEMENT SYSTEMS", "70.0", "83.33", "14/20"),
        )
    )
    year: str = "2026-27"
    term: str = "Odd"
    period: tuple[str, str] = ("07-07-26", "18-09-26")
    mentor: str = "Prof. Asha Mehulbhai Patel"
    # For tests of damaged letters: the enrollment at the end of the outward number.
    outward_enrollment: str | None = None
    # Text drawn twice, a hair apart, as some generators do for bold.
    fake_bold: bool = False
    # Row labels to print instead of 1, 2, 3..., to test a damaged table.
    numbers: tuple[str, ...] | None = None
    # A stray line printed between the table and the "Prof." line.
    note_under_table: str | None = None
    # Leave out the table's ruled lines.
    without_lines: bool = False


def _text(canvas, x, y, text, size=9, bold=False, fake_bold=False, right=False):
    canvas.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    draw = canvas.drawRightString if right else canvas.drawString
    draw(x, y, text)
    if fake_bold:
        draw(x + 0.2, y, text)


def _page(canvas, letter: Letter) -> None:
    width, height = A4
    outward = letter.outward_enrollment or letter.enrollment
    _text(canvas, 50, height - 50, f"Outward No: GCET/{letter.year}/{letter.term}/CP/{outward}/", 8)
    _text(canvas, width - 50, height - 75, "G H PATEL COLLEGE OF", 11, bold=True, right=True)
    _text(canvas, width - 50, height - 89, "ENGINEERING & TECHNOLOGY", 11, bold=True, right=True)
    _text(canvas, 50, height - 120, "Date: 21-09-26")
    _text(canvas, 70, height - 142, "To,")
    _text(canvas, 80, height - 155, letter.parent)
    _text(canvas, 80, height - 167, "12, Sample Society, Near Sample School")
    _text(canvas, 80, height - 179, "Pincode : 388120")
    subject = f"Subject : Regarding Attendance Report of {letter.student} ({letter.enrollment})"
    _text(canvas, 50, height - 205, subject, fake_bold=letter.fake_bold)
    _text(canvas, 50, height - 219, "Vishay: tamara palya ni hajri babat", 8)
    _text(canvas, 50, height - 240, "Dear Parent,")
    pronoun = "Her" if letter.child == "daughter" else "His"
    paragraph = Paragraph(
        f"Your {letter.child} has been studying in our college. {pronoun} attendance report "
        f"of academic year {letter.year}, {letter.term} term is given below from "
        f"{letter.period[0]} to {letter.period[1]}. University's minimum attendance criteria "
        "must be fulfilled by all the students for appearing in university end semester "
        "examination.",
        _BODY,
    )
    _, used = paragraph.wrap(width - 100, 200)
    paragraph.drawOn(canvas, 50, height - 250 - used)
    cells = [[Paragraph(title, _CELL) for title in HEADER]]
    labels = letter.numbers or [str(n) for n in range(1, len(letter.rows) + 1)]
    for number, row in zip(labels, letter.rows, strict=True):
        values = [number, row.code, row.name, row.theory, row.practical, row.marks,
                  row.status]  # fmt: skip
        cells.append([Paragraph(escape(value), _CELL) for value in values])
    table = Table(cells, colWidths=WIDTHS)
    style = [("VALIGN", (0, 0), (-1, -1), "TOP")]
    if not letter.without_lines:
        style.append(("GRID", (0, 0), (-1, -1), 0.5, colors.black))
    table.setStyle(TableStyle(style))
    _, table_height = table.wrap(0, 0)
    top = height - 340
    table.drawOn(canvas, 50, top - table_height)
    if letter.note_under_table:
        _text(canvas, 60, top - table_height - 15, letter.note_under_table, 7)
    _text(canvas, 50, top - table_height - 45, letter.mentor, fake_bold=letter.fake_bold)
    _text(canvas, width / 2, 90, "THE CHARUTAR VIDYA MANDAL (CVM) UNIVERSITY", 8, bold=True)
    _text(canvas, width / 2, 78, "Bakrol Road, Vallabh Vidyanagar-388120 (GUJ).", 7)


def make_letters(letters: list[Letter], blank_pages: tuple[int, ...] = ()) -> bytes:
    """One page per letter. A page number in `blank_pages` gets only a drawn box and no
    text, as a scanned page would."""
    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=A4)
    for number, letter in enumerate(letters, start=1):
        if number in blank_pages:
            canvas.rect(50, 50, 400, 600)
        else:
            _page(canvas, letter)
        canvas.showPage()
    canvas.save()
    return buffer.getvalue()


def name_for(number: int) -> str:
    """A made-up word for a number, letters only, like "BCA" for 120."""
    return "".join("ABCDEFGHIJ"[int(digit)] for digit in str(number))


def letter_for(number: int, **changes) -> Letter:
    """The default letter for student `number`, with its own enrollment and name."""
    base = Letter(
        enrollment=f"125020405{number:05}",
        student=f"SAMPLE {name_for(number)} KUMAR",
        parent=f"SAMPLE {name_for(number)}BHAI",
    )
    return replace(base, **changes)
