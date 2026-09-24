import json
import re

import pytest

from parent_notifier.core.extensions import db
from parent_notifier.services.imports.apply import apply_import
from parent_notifier.services.imports.sheet_parser import parse_sheet
from tests.factories.academics import make_class, make_semester, make_student
from tests.factories.accounts import make_mentor

HEADER = ["Enrollment No", "Student Name", "Parent Name", "Parent Phone", "DBMS", "OS"]
ROWS = [
    ["23CE001", "Avi Shah", "Mehul Shah", "9000000101", "Theory=70,Marks=16", "Marks=AB"],
    ["23CE002", "</script><b>x</b>", "Nilesh", "123", "Theory=90,Marks=5", "Theory=88"],
]


@pytest.fixture
def setup(app, mentor):
    with app.app_context():
        class_group = make_class(mentor)
        semester = make_semester(class_group, 4)
        apply_import(class_group, semester, mentor.id, "s", parse_sheet([HEADER, *ROWS], 20), False)
        outsider = make_student(class_group, "23CE099", full_name="Not In Sem 4")
        ids = {student.enrollment_no: student.id for student in semester.students}
        return f"/classes/{class_group.id}/sem/4", ids, outsider.id


def _data(html):
    block = re.search(
        r'<script type="application/json" id="students-data">(.*?)</script>', html, re.S
    )
    return json.loads(block.group(1))


def test_names_open_the_popup_or_the_student_page(signed_in_client, setup):
    base, ids, _ = setup
    html = signed_in_client.get(base).get_data(as_text=True)
    assert f'data-student-link="{ids["23CE001"]}"' in html
    assert f'href="{base}/students/{ids["23CE001"]}"' in html
    assert '<dialog id="student-popup"' in html
    assert 'data-midsem-max="20"' in html


def test_popup_data_carries_flags_for_each_subject(signed_in_client, setup):
    base, ids, _ = setup
    avi = next(
        s
        for s in _data(signed_in_client.get(base).get_data(as_text=True))
        if s["id"] == ids["23CE001"]
    )
    assert avi["badge"] == "at_risk"
    assert avi["phone"] == "+91 90000 00101"
    dbms, os_ = avi["subjects"]
    assert (dbms["theory"], dbms["theoryShort"], dbms["fail"]) == (70, True, False)
    assert (os_["absent"], os_["fail"]) == (True, True)


def test_data_block_cannot_be_broken_out_of(signed_in_client, setup):
    base, _, _ = setup
    html = signed_in_client.get(base).get_data(as_text=True)
    assert "</script><b>x</b>" not in html
    names = [student["name"] for student in _data(html)]
    assert "</script><b>x</b>" in names


def test_popup_data_follows_the_filter(signed_in_client, setup):
    base, _, _ = setup
    html = signed_in_client.get(f"{base}?status=at_risk").get_data(as_text=True)
    assert [student["enrollment"] for student in _data(html)] == ["23CE001"]


def test_student_page_works_without_javascript(signed_in_client, setup):
    base, ids, _ = setup
    html = signed_in_client.get(f"{base}/students/{ids['23CE002']}").get_data(as_text=True)
    assert "&lt;/script&gt;&lt;b&gt;x&lt;/b&gt;" in html
    assert "not a valid mobile number" in html
    assert (
        '<span class="figure-fail">5/20</span><span class="visually-hidden"> (below the pass mark)'
        in html
    )


def test_student_outside_the_semester_is_not_found(signed_in_client, setup):
    base, _, outsider = setup
    assert signed_in_client.get(f"{base}/students/{outsider}").status_code == 404


def test_another_mentors_student_is_not_found(app, signed_in_client):
    with app.app_context():
        stranger = make_mentor(username="niravshah", whatsapp_number="+919000000002")
        class_group = make_class(stranger, name="IT-B")
        semester = make_semester(class_group, 4)
        student = make_student(class_group, "23IT001")
        semester.students.append(student)
        db.session.commit()
        url = f"/classes/{class_group.id}/sem/4/students/{student.id}"
    assert signed_in_client.get(url).status_code == 404


def test_student_page_needs_sign_in(client, setup):
    base, ids, _ = setup
    response = client.get(f"{base}/students/{ids['23CE001']}")
    assert response.headers["Location"].startswith("/sign-in")


def test_popup_carries_the_one_english_and_gujarati_message(signed_in_client, setup):
    base, ids, _ = setup
    html = signed_in_client.get(base).get_data(as_text=True)
    assert "popup-language" not in html  # no language to choose
    avi = next(s for s in _data(html) if s["id"] == ids["23CE001"])
    assert avi["messages"]["plain"].startswith("Dear Parent,\nઆદરણીય વાલીશ્રી,")
