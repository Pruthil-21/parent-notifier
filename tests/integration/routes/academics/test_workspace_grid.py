import re

import pytest

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup
from parent_notifier.services.imports.apply import apply_import
from parent_notifier.services.imports.sheet_parser import parse_sheet
from tests.factories.academics import make_class, make_semester

HEADER = ["Enrollment No", "Student Name", "Parent Name", "Parent Phone", "DBMS", "OS"]
ROWS = [
    ["23CE001", "Avi Shah", "Mehul Shah", "9000000101", "Theory=70,Marks=16", "Theory=80"],
    ["23CE002", "Om Desai", "Nilesh Desai", "9000000102", "Theory=90,Marks=5", "Theory=88"],
    ["23CE003", "Riya Patel", "Kiran Patel", "9000000103", "Theory=90,Marks=15", "Marks=AB"],
    ["23CE004", "Isha Joshi", "Hetal Joshi", "9000000104", "Theory=95,Marks=18", "Theory=91"],
]


@pytest.fixture
def base(app, mentor):
    with app.app_context():
        class_group = make_class(mentor)
        semester = make_semester(class_group, 4)
        sheet = parse_sheet([HEADER, *ROWS], 20)
        apply_import(class_group, semester, mentor.id, "s.xlsx", sheet, update_identity=False)
        return f"/classes/{class_group.id}/sem/4"


def test_tiles_count_each_band(signed_in_client, base):
    html = signed_in_client.get(base).get_data(as_text=True)
    assert "4 students · 2 subjects" in html
    for label, count in (("At risk", 1), ("Needs attention", 2), ("Doing well", 1)):
        tile = rf'tile__label">{label}</span>\s*<span class="tile__value numeric">{count}<'
        assert re.search(tile, html)


def test_grid_shows_figures_and_badges(signed_in_client, base):
    html = signed_in_client.get(base).get_data(as_text=True)
    assert ">Avi Shah</a></th>" in html
    assert '<span class="figure-short">70%</span>' in html
    assert '<span class="figure-fail">Fail</span>' in html
    assert "DBMS 5/20" in html
    assert '<span class="figure-fail">Absent</span>' in html
    assert "Avg 16/20" in html
    assert '<span class="badge badge--at-risk">At risk</span>' in html


def test_left_students_leave_the_grid_and_tiles(app, signed_in_client, base):
    with app.app_context():
        semester = db.session.scalars(db.select(ClassGroup)).first().semesters[0]
        next(s for s in semester.students if s.enrollment_no == "23CE001").status = "left"
        db.session.commit()
    html = signed_in_client.get(base).get_data(as_text=True)
    assert "Avi Shah" not in html
    assert '<span class="tile__value numeric">3</span>' in html


def test_names_in_the_grid_are_escaped(app, signed_in_client, mentor):
    with app.app_context():
        class_group = make_class(mentor, name="CE-X")
        semester = make_semester(class_group, 1)
        rows = [["23CE009", "<img src=x onerror=alert(1)>", "P", "9000000109", "Theory=80", ""]]
        apply_import(class_group, semester, mentor.id, "s", parse_sheet([HEADER, *rows], 20), False)
        url = f"/classes/{class_group.id}/sem/1"
    html = signed_in_client.get(url).get_data(as_text=True)
    assert "<img src=x" not in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html


def test_tiles_link_to_filtered_lists(signed_in_client, base):
    html = signed_in_client.get(base).get_data(as_text=True)
    assert f'href="{base}?status=at_risk"' in html
    filtered = signed_in_client.get(f"{base}?status=at_risk").get_data(as_text=True)
    assert "Showing 1 of 4 students" in filtered
    assert "Avi Shah" in filtered
    assert "Om Desai" not in filtered.split("<tbody>")[1]
    assert 'aria-current="true"' in filtered


def test_search_and_sort_from_the_query_string(signed_in_client, base):
    html = signed_in_client.get(f"{base}?q=patel&sort=name&dir=desc").get_data(as_text=True)
    assert "Showing 1 of 4 students" in html
    assert 'value="patel"' in html
    assert 'aria-sort="descending"' in html


def test_no_match_offers_to_clear(signed_in_client, base):
    html = signed_in_client.get(f"{base}?q=nobody").get_data(as_text=True)
    assert "No students match." in html
    assert "Clear the search and filter" in html


def test_left_students_have_their_own_filter(app, signed_in_client, base):
    with app.app_context():
        semester = db.session.scalars(db.select(ClassGroup)).first().semesters[0]
        next(s for s in semester.students if s.enrollment_no == "23CE001").status = "left"
        db.session.commit()
    html = signed_in_client.get(f"{base}?status=inactive").get_data(as_text=True)
    assert "Avi Shah" in html
    assert '<span class="badge badge--left">Left</span>' in html
