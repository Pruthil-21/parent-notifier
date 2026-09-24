"""The home page must show exactly what each class's semester page shows."""

import re

import pytest

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import Student
from parent_notifier.services.messaging import send_log
from tests.factories.academics import import_sheet, make_class, make_semester

EXTRA = [
    ["23CE005", "Kavya Rao", "Suresh Rao", "9000000105", "Theory=60", "Theory=62"],
    ["23CE006", "Neel Vora", "Paresh Vora", "9000000106", "Theory=65", "Theory=90"],
    ["23CE007", "Tara Modi", "Anil Modi", "12345", "Theory=91", "Theory=92"],
]


def _set_status(enrollment_no: str, status: str) -> None:
    student = db.session.scalars(db.select(Student).filter_by(enrollment_no=enrollment_no)).one()
    student.status = status
    db.session.commit()


@pytest.fixture
def classes(app, mentor):
    """Two classes. In CE-A a student at risk has left, another is detained, one parent
    has no valid number, one was messaged and one skipped."""
    with app.app_context():
        ce_a = make_class(mentor, name="CE-A")
        import_sheet(ce_a, make_semester(ce_a, 3), mentor.id)
        sem4 = make_semester(ce_a, 4)
        import_sheet(ce_a, sem4, mentor.id)
        import_sheet(ce_a, sem4, mentor.id, rows=EXTRA)
        _set_status("23CE005", "left")
        _set_status("23CE004", "detained")
        for enrollment_no, status in (("23CE002", "sent"), ("23CE003", "skipped")):
            student = db.session.scalars(
                db.select(Student).filter_by(enrollment_no=enrollment_no)
            ).one()
            send_log.record(
                sem4, student.id, mentor.id, status=status, language="en", note="", message=""
            )
        ce_b = make_class(mentor, name="CE-B", admission_year=2024)
        import_sheet(ce_b, make_semester(ce_b, 2), mentor.id, rows=EXTRA)
        return [(ce_a.id, 4), (ce_b.id, 2)]


def semester_counts(client, class_id: int, number: int) -> tuple[int, int, int]:
    html = client.get(f"/classes/{class_id}/sem/{number}").get_data(as_text=True)

    def tile(label):
        found = re.search(
            rf'tile__label">{label}</span>\s*<span class="tile__value numeric">(\d+)<', html
        )
        return int(found.group(1))

    pending = re.search(r"Message pending parents \((\d+)\)", html)
    return tile("Students"), tile("At risk"), int(pending.group(1)) if pending else 0


def home_counts(html: str, class_id: int) -> tuple[int, int, int]:
    row = re.search(
        rf'<tr>\s*<th scope="row"><a href="/classes/{class_id}">.*?</tr>', html, re.S
    ).group(0)
    cells = re.findall(r'<td class="numeric">\s*(?:<[^>]+>)*\s*(\d+)', row)
    _batch, students, at_risk, pending = (int(cell) for cell in cells)
    return students, at_risk, pending


def test_class_rows_match_their_semester_pages(signed_in_client, classes):
    home = signed_in_client.get("/").get_data(as_text=True)
    for class_id, number in classes:
        assert home_counts(home, class_id) == semester_counts(signed_in_client, class_id, number)


def test_tiles_add_up_the_semester_pages(signed_in_client, classes):
    home = signed_in_client.get("/").get_data(as_text=True)
    pages = [semester_counts(signed_in_client, *place) for place in classes]
    for label, index in (("Students at risk", 1), ("Parents to message", 2)):
        tile = rf'tile__label">{label}</span>\s*<span class="tile__value numeric">(\d+)<'
        assert int(re.search(tile, home).group(1)) == sum(page[index] for page in pages)


def test_left_and_detained_students_are_not_counted(signed_in_client, classes):
    home = signed_in_client.get("/").get_data(as_text=True)
    # CE-A Sem 4 holds seven students: one left and one detained leave five, of whom
    # 23CE001 and 23CE006 are at risk and still pending; 23CE007 has no valid number,
    # 23CE002 was messaged and 23CE003 skipped.
    assert home_counts(home, classes[0][0]) == (5, 2, 2)
