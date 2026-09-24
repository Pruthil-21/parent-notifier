import random
from dataclasses import replace
from datetime import date, timedelta

import pytest
from reportlab.pdfgen.canvas import Canvas

from parent_notifier.services.imports.letters import (
    LetterFileError,
    LetterSubject,
    read_letters,
)
from tests.factories.letters import Letter, Row, letter_for, make_letters

FIRST = [
    LetterSubject("102003406", "PROBABILITY STATISTICS AND NUMERICAL METHODS", 71.88, 60, 20, False, 20),  # noqa: E501
    LetterSubject("102003407", "Entrepreneurship Skills", 63.64, None, 18, False, 25),
    LetterSubject("102003411", "UNIVERSAL HUMAN VALUES", 46.15, None, 0, False, 25),
    LetterSubject("102040304", "DATA STRUCTURES", 73.08, 77.78, 17, False, 20),
    LetterSubject("102040305", "DATABASE MANAGEMENT SYSTEMS", 70, 83.33, 14, False, 20),
]  # fmt: skip


def _one(letter: Letter, **options):
    result = read_letters(make_letters([letter], **options))
    return result.letters[0] if result.letters else None, result.problems


def test_every_field_of_a_letter_is_read_exactly():
    letter, problems = _one(Letter(fake_bold=True))  # doubled characters are merged
    assert problems == []
    assert (letter.enrollment, letter.student_name, letter.parent_name) == (
        "12502040500001",
        "PATEL RIYA KIRANBHAI",
        "PATEL KIRANBHAI",
    )
    assert (letter.gender, letter.year, letter.term, letter.mentor) == (
        "female",
        "2026-27",
        "Odd",
        "Prof. Asha Mehulbhai Patel",
    )
    assert (letter.attendance_from, letter.attendance_to) == (date(2026, 7, 7), date(2026, 9, 18))
    assert list(letter.subjects) == FIRST


def test_a_son_and_a_table_without_ruled_lines_are_read_too():
    letter, problems = _one(Letter(child="son", without_lines=True, term="Even"))
    assert problems == [] and letter.gender == "male" and letter.term == "Even"
    assert list(letter.subjects) == FIRST


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"outward_enrollment": "12502040599999"}, "differs from the one in its Outward No"),
        ({"numbers": ("1", "2", "4", "5", "6")}, "not numbered 1, 2, 3... (row 3)"),
        ({"period": ("18-09-26", "07-07-26")}, "attendance period ends before it starts"),
        ({"period": ("31-02-26", "18-09-26")}, "are not real dates"),
        # The ruled cells leave the stray line out and the text reading takes it in.
        ({"note_under_table": "Note: 21 days of leave were granted"}, "reads differently"),
    ],
)
def test_a_damaged_page_is_refused_with_its_reason(changes, reason):
    letter, problems = _one(replace(Letter(), **changes))
    assert letter is None
    assert len(problems) == 1 and problems[0].startswith("Page 1: ") and reason in problems[0]


@pytest.mark.parametrize(
    ("row", "reason"),
    [
        (Row("102003406", "DATA STRUCTURES", "120", "60", "17/20"), '"120" is not a percentage'),
        (Row("102003406", "DATA STRUCTURES", "71.5%", "60", "17/20"), "is not a percentage"),
        (Row("102003406", "DATA STRUCTURES", "71", "60", "21/20"), "more than the total"),
        (Row("102003406", "DATA STRUCTURES", "71", "60", "17"), "are not like 17/20"),
        (Row("1020 03406", "DATA STRUCTURES", "71", "60", "17/20"), "has subject code"),
    ],
)
def test_a_figure_that_is_not_exact_refuses_the_page(row, reason):
    letter, problems = _one(Letter(rows=(row,)))
    assert letter is None and reason in problems[0]


def test_absent_and_missing_marks_and_a_repeated_code():
    rows = (
        Row("102003406", "DATA STRUCTURES", "71", "-", "AB"),
        Row("102003407", "OS", "-", "-", "-"),
    )
    letter, _ = _one(Letter(rows=rows))
    assert [(s.marks, s.absent, s.theory) for s in letter.subjects] == [
        (None, True, 71),
        (None, False, None),
    ]
    twice = (rows[0], replace(rows[1], code="102003406"))
    assert "appears twice" in _one(Letter(rows=twice))[1][0]


def test_a_scanned_page_is_refused_and_the_others_read():
    result = read_letters(make_letters([letter_for(1), letter_for(2)], blank_pages=(2,)))
    assert [letter.page for letter in result.letters] == [1]
    assert result.problems == ["Page 2: it has no text to read, so it may be a scan"]


def test_files_that_are_not_readable_letters_are_refused(tmp_path):
    with pytest.raises(LetterFileError, match="could not be read as a PDF"):
        read_letters(b"%PDF-1.4 this is not really a PDF")
    locked = tmp_path / "locked.pdf"
    canvas = Canvas(str(locked), encrypt="secret")
    canvas.drawString(100, 700, "Outward No: GCET/2026-27/Odd/CP/12502040500001/")
    canvas.save()
    with pytest.raises(LetterFileError, match="locked with a password"):
        read_letters(locked.read_bytes())


def _random_letter(rng: random.Random, number: int) -> tuple[Letter, list[LetterSubject]]:
    words = ["DATA", "STRUCTURES", "DATABASE", "MANAGEMENT", "SYSTEMS", "Digital", "Signal",
             "PROCESSING", "AND", "OF", "Mathematics", "II", "Operating", "Theory", "Computer",
             "NETWORKS", "Engineering", "Graphics", "Universal", "Human", "Values"]  # fmt: skip
    rows, expected = [], []
    for index in range(rng.randint(1, 9)):
        code = f"10{rng.randint(1000000, 9999999)}{index}"[:9]
        code = f"{code[:8]}{index}"
        name = " ".join(rng.choice(words) for _ in range(rng.randint(1, 7)))
        theory = rng.choice(["-", str(rng.randint(0, 100)), f"{rng.uniform(0, 100):.2f}"])
        practical = rng.choice(["-", f"{rng.uniform(0, 100):.1f}", "100"])
        total = rng.choice([20, 25])
        marks = rng.choice(["-", "AB", f"{rng.randint(0, total)}/{total}"])
        status = rng.choice(["Satisfactory", "Not Satisfactory", "Not Applicable"])
        rows.append(Row(code, name, theory, practical, marks, status))
        mid, absent, out_of = None, False, None
        if marks == "AB":
            absent = True
        elif marks != "-":
            mid, out_of = float(marks.split("/")[0]), total
        expected.append(
            LetterSubject(
                code,
                name,
                None if theory == "-" else float(theory),
                None if practical == "-" else float(practical),
                mid,
                absent,
                out_of,
            )
        )
    start = date(2026, 1, 1) + timedelta(days=rng.randint(0, 200))
    end = start + timedelta(days=rng.randint(0, 120))
    letter = letter_for(
        number,
        rows=tuple(rows),
        child=rng.choice(["son", "daughter"]),
        period=(start.strftime("%d-%m-%y"), end.strftime("%d-%m-%y")),
        fake_bold=rng.random() < 0.3,
    )
    return letter, expected


@pytest.mark.parametrize("seed", range(12))
def test_random_classes_read_back_exactly(seed):
    """Round trip: made-up letters with random subjects, figures and wrapping must come
    back field for field, with nothing refused, lost or added."""
    rng = random.Random(seed)  # noqa: S311  (made-up test data, not secrets)
    made = [_random_letter(rng, number) for number in range(1, rng.randint(2, 6))]
    result = read_letters(make_letters([letter for letter, _ in made]))
    assert result.problems == []
    assert len(result.letters) == len(made)
    for read, (letter, expected) in zip(result.letters, made, strict=True):
        assert read.enrollment == letter.enrollment and read.student_name == letter.student
        assert read.gender == {"son": "male", "daughter": "female"}[letter.child]
        assert read.attendance_from.strftime("%d-%m-%y") == letter.period[0]
        assert list(read.subjects) == expected
