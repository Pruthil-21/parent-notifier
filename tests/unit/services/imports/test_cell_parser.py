import pytest

from parent_notifier.services.imports.cell_parser import (
    CellError,
    SubjectCell,
    format_cell,
    parse_cell,
)

FULL = SubjectCell(theory=86, practical=92, marks=16)


@pytest.mark.parametrize(
    "text",
    [
        "Theory=86,Practical=92,Marks=16",
        "theory=86, practical=92, marks=16",
        "Theory: 86; Practical: 92; Marks: 16",
        "Theory=86|Practical=92|Marks=16",
        "Theory=86\nPractical=92\nMarks=16",
        "Th=86%,Pr=92%,Mid=16/20",
        "THEORY = 86 , PRAC = 92 , Mid-Sem = 16",
        "Marks=16,Theory=86,Practical=92,",
    ],
)
def test_every_accepted_way_of_typing_a_cell(text):
    assert parse_cell(text, 20) == FULL


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Theory=79,Marks=AB", SubjectCell(theory=79, absent=True)),
        ("Theory=79,Marks=absent", SubjectCell(theory=79, absent=True)),
        ("Theory=82.5,Practical=", SubjectCell(theory=82.5)),
        ("Theory=70,Practical=NA,Marks=-", SubjectCell(theory=70)),
        ("Marks=0", SubjectCell(marks=0)),
        ("Theory=100,Marks=20", SubjectCell(theory=100, marks=20)),
    ],
)
def test_blank_absent_and_edge_values(text, expected):
    assert parse_cell(text, 20) == expected


@pytest.mark.parametrize("text", [None, "", "   "])
def test_blank_cell_means_no_data_yet(text):
    assert parse_cell(text, 20).is_empty


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("Theory=120", "Theory must be a percentage from 0 to 100"),
        ("Practical=-5", "Practical must be a percentage from 0 to 100"),
        ("Theory=eighty", "Theory must be a percentage from 0 to 100"),
        ("Theory=80/100", "Theory must be a percentage from 0 to 100"),
        ("Marks=25", "Marks must be from 0 to 20"),
        ("Marks=16/30", "Marks must be out of 20 for this class"),
        ("Marks=80%", "Marks must be a number from 0 to 20, or AB if absent"),
        ("Lab=90", 'Unknown part "Lab"'),
        ("Theory=80,Theory=81", "Theory appears twice"),
        ("86,92,16", '"86" is not in the form Theory=86'),
    ],
)
def test_problems_are_explained(text, message):
    with pytest.raises(CellError, match=message):
        parse_cell(text, 20)


def test_marks_follow_the_class_total():
    assert parse_cell("Marks=27/30", 30) == SubjectCell(marks=27)


def test_a_bare_number_from_excel_is_not_a_cell():
    with pytest.raises(CellError, match="is not in the form Theory=86"):
        parse_cell(86, 20)


@pytest.mark.parametrize(
    "cell",
    [
        FULL,
        SubjectCell(theory=82.5, absent=True),
        SubjectCell(theory=70),
        SubjectCell(marks=0),
        SubjectCell(),
    ],
)
def test_format_round_trips(cell):
    assert parse_cell(format_cell(cell), 20) == cell


def test_format_reads_like_the_sheet_format():
    assert format_cell(FULL) == "Theory=86,Practical=92,Marks=16"
    assert format_cell(SubjectCell(theory=79, absent=True)) == "Theory=79,Marks=AB"
