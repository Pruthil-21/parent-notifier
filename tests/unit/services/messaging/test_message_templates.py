import pytest

from parent_notifier.services.academics.risk import SubjectResult
from parent_notifier.services.messaging import message_templates
from parent_notifier.services.messaging.message_templates import render_message, signature

COLLEGE = "G. H. Patel College of Engineering & Technology"
RESULTS = [
    SubjectResult("Data Structures", theory=86, practical=92, marks=16),
    SubjectResult("Probability & Statistics", theory=71, absent=True),
    SubjectResult("Digital Electronics", theory=88, practical=79),
]
APPROVED = """Dear Parent,

This is regarding Avi Shah's (Enrollment No. 230120107001) academic attendance and performance for Sem 3.
The details are as follows:
1. Data Structures: Theory – 86%, Practical – 92%, Mid-Sem – 16/20
2. Probability & Statistics: Theory – 71%, Practical – N/A, Mid-Sem – AB
3. Digital Electronics: Theory – 88%, Practical – 79%, Mid-Sem – --/20

Kindly take note of the above attendance and academic performance and guide your ward to attend classes and practical sessions regularly and focus on studies.

You are free to meet the mentor between 9:00 AM and 5:00 PM on working days for any clarification or discussion.

Regards,
Prof. Pruthil Mistry
G. H. Patel College of Engineering & Technology"""  # noqa: E501, RUF001


def render(**changes):
    values = {
        "student_name": "Avi Shah",
        "enrollment_no": "230120107001",
        "semester": 3,
        "results": RESULTS,
        "midsem_max": 20,
        "mentor_name": "Pruthil Mistry",
        "college_name": COLLEGE,
    }
    return render_message("en", **(values | changes))


def test_matches_the_approved_wording_exactly():
    assert render() == APPROVED


def test_note_line_appears_only_when_a_note_is_given():
    text = render(note="  Please meet me on Monday about the DBMS practicals.  ")
    assert (
        "\n\nNote from the mentor: Please meet me on Monday about the DBMS practicals.\n\n" in text
    )
    assert "Note from the mentor" not in render(note="   ")


@pytest.mark.parametrize(
    ("name", "expected"),
    [("Pruthil Mistry", "Prof. Pruthil Mistry"), ("Prof. Asha Patel", "Prof. Asha Patel")],
)
def test_prof_is_not_doubled(name, expected):
    assert signature(name, "en") == expected


def test_decimals_and_other_totals():
    text = render(results=[SubjectResult("OS", theory=82.5, marks=27)], midsem_max=30)
    assert "1. OS: Theory – 82.5%, Practical – N/A, Mid-Sem – 27/30" in text  # noqa: RUF001


def test_student_data_is_a_value_never_template_code():
    text = render(student_name="{{ 7 * 7 }} {% raw %}")
    assert "{{ 7 * 7 }} {% raw %}'s" in text


def test_edited_template_is_picked_up_without_a_restart(tmp_path, monkeypatch):
    (tmp_path / "parent_report.en.txt").write_text("Hello {{ student_name }}", encoding="utf-8")
    environment = message_templates._environment.overlay(
        loader=message_templates.FileSystemLoader(tmp_path)
    )
    monkeypatch.setattr(message_templates, "_environment", environment)
    assert render() == "Hello Avi Shah"
    (tmp_path / "parent_report.en.txt").write_text("Hi {{ student_name }}", encoding="utf-8")
    environment.cache.clear()
    assert render() == "Hi Avi Shah"
