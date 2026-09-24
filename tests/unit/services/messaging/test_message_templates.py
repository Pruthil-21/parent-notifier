from datetime import date

import pytest

from parent_notifier.services.academics.views.risk import SubjectResult
from parent_notifier.services.messaging import message_templates
from parent_notifier.services.messaging.message_templates import render_message, signature

COLLEGE = "G. H. Patel College of Engineering & Technology"
RESULTS = [
    SubjectResult("Data Structures", theory=86, practical=92, marks=16),
    SubjectResult("Probability & Statistics", theory=71, absent=True),
    SubjectResult("Digital Electronics", theory=88, practical=79),
]
# The wording approved on 2026-09-25: each part in English, then Gujarati.
APPROVED = """Dear Parent,
આદરણીય વાલીશ્રી,

This is regarding the attendance and academic performance of your daughter Riya Patel (Enrollment No. 12502040500001) for Sem 3, from 07-07-26 to 18-09-26.
આપની પુત્રી Riya Patel (એનરોલમેન્ટ નં. 12502040500001) ની સેમ 3 ની તા. 07-07-26 થી તા. 18-09-26 સુધીની હાજરી અને શૈક્ષણિક પ્રગતિની વિગતો નીચે મુજબ છે:

1. Data Structures: Theory – 86%, Practical – 92%, Mid-Sem – 16/20
2. Probability & Statistics: Theory – 71%, Practical – N/A, Mid-Sem – AB
3. Digital Electronics: Theory – 88%, Practical – 79%, Mid-Sem – --/20

Kindly take note of the above attendance and academic performance and guide her to attend classes and practical sessions regularly and focus on studies.
ઉપરોક્ત હાજરી અને શૈક્ષણિક પ્રગતિની નોંધ લઈ, તેને નિયમિત રીતે વર્ગો અને પ્રેક્ટિકલ સત્રોમાં હાજર રહેવા તથા અભ્યાસ પર ધ્યાન આપવા માર્ગદર્શન આપશો.

You are free to meet the mentor between 9:00 AM and 5:00 PM on working days for any clarification or discussion.
કોઈ પણ સ્પષ્ટતા કે ચર્ચા માટે આપ કાર્યકારી દિવસોમાં સવારે 9:00 થી સાંજે 5:00 દરમિયાન મેન્ટરને મળી શકો છો.

Regards,
આભાર સહ,
Prof. Pruthil Mistry
G. H. Patel College of Engineering & Technology"""  # noqa: E501, RUF001


def render(**changes):
    values = {
        "student_name": "Riya Patel",
        "enrollment_no": "12502040500001",
        "semester": 3,
        "results": RESULTS,
        "midsem_max": 20,
        "mentor_name": "Pruthil Mistry",
        "college_name": COLLEGE,
        "gender": "female",
        "attendance_from": date(2026, 7, 7),
        "attendance_to": date(2026, 9, 18),
    }
    return render_message(**(values | changes))


def test_matches_the_approved_wording_exactly():
    assert render() == APPROVED


def test_a_son_or_an_unknown_ward_and_no_dates():
    son = render(gender="male")
    assert "of your son Riya Patel" in son and "આપના પુત્ર Riya Patel" in son
    assert "guide him to attend" in son
    ward = render(gender=None, attendance_from=None)  # one end missing: no period at all
    assert "of your ward Riya Patel (Enrollment No. 12502040500001) for Sem 3.\n" in ward
    assert "આપના પાલ્ય Riya Patel (એનરોલમેન્ટ નં. 12502040500001) ની સેમ 3 ની હાજરી" in ward
    assert "guide your ward to attend" in ward and "તા." not in ward


def test_note_line_appears_only_when_a_note_is_given():
    text = render(note="  Please meet me on Monday about the DBMS practicals.  ")
    assert (
        "\n\nNote from the mentor / મેન્ટરની નોંધ: Please meet me on Monday about the DBMS "
        "practicals.\n\nRegards," in text
    )
    assert "Note from the mentor" not in render(note="   ")


@pytest.mark.parametrize(
    ("name", "expected"),
    [("Pruthil Mistry", "Prof. Pruthil Mistry"), ("Prof. Asha Patel", "Prof. Asha Patel")],
)
def test_prof_is_not_doubled(name, expected):
    assert signature(name) == expected


def test_decimals_and_other_totals():
    text = render(results=[SubjectResult("OS", theory=82.5, marks=27)], midsem_max=30)
    assert "1. OS: Theory – 82.5%, Practical – N/A, Mid-Sem – 27/30" in text  # noqa: RUF001


def test_student_data_is_a_value_never_template_code():
    text = render(student_name="{{ 7 * 7 }} {% raw %}")
    assert "your daughter {{ 7 * 7 }} {% raw %} (Enrollment" in text


def test_edited_template_is_picked_up_without_a_restart(tmp_path, monkeypatch):
    template = tmp_path / message_templates.TEMPLATE
    template.write_text("Hello {{ student_name }}", encoding="utf-8")
    environment = message_templates._environment.overlay(
        loader=message_templates.FileSystemLoader(tmp_path)
    )
    monkeypatch.setattr(message_templates, "_environment", environment)
    assert render() == "Hello Riya Patel"
    template.write_text("Hi {{ student_name }}", encoding="utf-8")
    environment.cache.clear()
    assert render() == "Hi Riya Patel"
