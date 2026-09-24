import io
import re
from dataclasses import replace
from datetime import date

import pytest
from sqlalchemy import select

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import Semester, SemesterSubject, Student
from tests.factories.academics import make_class, make_semester, make_student
from tests.factories.letters import letter_for, make_letters


@pytest.fixture
def class_ids(app, mentor):
    """A 2025 class in Sem 3 whose list holds students 1 and 2 (as the class writes them)."""
    with app.app_context():
        class_group = make_class(mentor, admission_year=2025)
        make_semester(class_group, 3)
        make_semester(class_group, 4)
        for number, name in ((1, "Sample B Kumar"), (2, "Kumar Sample C")):
            make_student(
                class_group,
                letter_for(number).enrollment,
                full_name=name,
                parent_name="",
                phone_raw=f"90000 0010{number}",
                phone_e164=f"+91900000010{number}",
            )
        return class_group.id


def _upload(client, class_id, letters, number=3, **options):
    data = {"sheet": (io.BytesIO(make_letters(letters, **options)), "letters.pdf")}
    return client.post(
        f"/classes/{class_id}/sem/{number}/import", data=data, content_type="multipart/form-data"
    ).get_data(as_text=True)


def _token(html):
    found = re.search(r'name="token" value="([0-9a-f]{32})"', html)
    return found.group(1) if found else None


def test_letters_are_reviewed_then_saved_filling_only_blanks(app, signed_in_client, class_ids):
    letters = [letter_for(1), letter_for(2, child="son"), letter_for(3)]
    html = _upload(signed_in_client, class_ids, letters)
    assert "3 of 3" in html and "2026-27, Odd term" in html and "07-07-26 to 18-09-26" in html
    assert "All 3 students, one per page" in html and "Prof. Asha Mehulbhai Patel" in html
    assert "1 student is not on the class list (page 3)" in html
    assert "Update these details" not in html  # letters never replace saved details
    signed_in_client.post(
        f"/classes/{class_ids}/sem/3/import/confirm", data={"token": _token(html)}
    )
    with app.app_context():
        semester = db.session.scalar(select(Semester).where(Semester.number == 3))
        assert (semester.attendance_from, semester.attendance_to) == (
            date(2026, 7, 7),
            date(2026, 9, 18),
        )
        totals = dict(
            db.session.execute(select(SemesterSubject.name, SemesterSubject.midsem_max)).all()
        )
        assert totals["Universal Human Values"] == 25 and totals["Data Structures"] is None
        students = {s.enrollment_no: s for s in db.session.scalars(select(Student))}
        first, second, new = (students[letter_for(n).enrollment] for n in (1, 2, 3))
        assert (first.full_name, first.gender, first.parent_name) == (
            "Sample B Kumar",  # the class list's spelling stays
            "female",
            "Sample Bbhai",  # was blank, so the letter fills it
        )
        assert (second.gender, new.full_name, new.phone_e164) == ("male", "Sample D Kumar", None)
        assert len(semester.students) == 3
    page = signed_in_client.get(f"/classes/{class_ids}/sem/3").get_data(as_text=True)
    assert "Mid-Sem \\u2013 0/25" in page  # in the message

    signed_in_client.post(f"/classes/{class_ids}/sem/3/import/undo")
    with app.app_context():
        restored = db.session.scalar(
            select(Student).where(Student.enrollment_no == letter_for(1).enrollment)
        )
        assert (restored.gender, restored.parent_name) == (None, "")


@pytest.mark.parametrize(
    ("letters", "number", "options", "problem"),
    [
        ([letter_for(1)], 4, {}, "are for the Odd term, but Sem 4 is an even semester"),
        ([letter_for(1, student="SHAH OM NILESHBHAI")], 3, {}, "does not match Sample B Kumar"),
        ([letter_for(1), letter_for(1)], 3, {}, "has a letter on pages 1, 2"),
        ([letter_for(1), letter_for(2)], 3, {"blank_pages": (2,)}, "Page 2: it has no text"),
        (
            [letter_for(1), letter_for(2, period=("07-07-26", "30-09-26"))],
            3,
            {},
            "do not all have the same attendance period",
        ),
    ],
)
def test_a_problem_anywhere_in_the_pdf_stops_the_import(
    signed_in_client, class_ids, letters, number, options, problem
):
    html = _upload(signed_in_client, class_ids, letters, number, **options)
    assert problem in html
    assert _token(html) is None  # nothing can be confirmed


def test_a_subject_code_must_keep_one_name(signed_in_client, class_ids):
    first = letter_for(1)
    renamed = replace(first.rows[0], name="STATISTICS")
    second = letter_for(2, rows=(renamed, *first.rows[1:]))
    html = _upload(signed_in_client, class_ids, [first, second])
    assert "Subject 102003406 has different names on different pages" in html
    assert _token(html) is None
