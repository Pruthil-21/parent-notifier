import re

import pytest
from sqlalchemy import select

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup
from tests.factories.academics import make_class
from tests.factories.accounts import make_mentor

VALID = {"name": " CE-A ", "department": "Computer   Engineering", "admission_year": "2023"}


@pytest.fixture
def own_class(app, mentor):
    with app.app_context():
        return make_class(mentor).id


@pytest.fixture
def strangers_class(app):
    with app.app_context():
        stranger = make_mentor(username="niravshah", whatsapp_number="+919000000002")
        return make_class(stranger, name="IT-B").id


def _classes(app):
    with app.app_context():
        return db.session.scalars(select(ClassGroup)).all()


@pytest.mark.parametrize("path", ["/classes/", "/classes/new", "/classes/1"])
def test_class_pages_need_sign_in(client, path):
    assert client.get(path).headers["Location"].startswith("/sign-in")


def test_empty_list_explains_the_first_step(signed_in_client):
    html = signed_in_client.get("/classes/").get_data(as_text=True)
    assert "No classes yet" in html
    assert 'href="/classes/new"' in html


def test_list_shows_the_mentors_classes_only(signed_in_client, own_class, strangers_class):
    html = signed_in_client.get("/classes/").get_data(as_text=True)
    assert f'href="/classes/{own_class}">CE-A</a>' in html
    assert "IT-B" not in html
    assert "None yet" in html
    assert "Not yet" in html


def test_new_class_is_created_and_opened(app, signed_in_client, mentor):
    response = signed_in_client.post("/classes/new", data=VALID)
    [class_group] = _classes(app)
    assert response.headers["Location"] == f"/classes/{class_group.id}"
    assert (class_group.name, class_group.department) == ("CE-A", "Computer Engineering")
    assert class_group.mentor_id == mentor.id
    html = signed_in_client.get(response.headers["Location"]).get_data(as_text=True)
    assert "Class CE-A created." in html
    assert "No semesters yet" in html
    assert "Computer Engineering · 2023 batch" in html


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("name", "", "Enter a class name"),
        ("name", "C" * 41, "Class name must be 40 characters or fewer"),
        ("name", "CE\u0007A", "Class name can only use letters"),
        ("department", "", "Choose the department"),
        ("department", "Physics", "Choose a department from the list"),
        ("admission_year", "", "Enter the admission year"),
        ("admission_year", "twenty", "Enter the admission year as 4 digits, like 2023"),
        ("admission_year", "1999", "Admission year must be between 2000 and"),
        ("admission_year", "2099", "Admission year must be between 2000 and"),
    ],
)
def test_each_problem_is_explained_and_nothing_is_saved(
    app, signed_in_client, field, value, message
):
    html = signed_in_client.post("/classes/new", data=VALID | {field: value}).get_data(as_text=True)
    assert "There is a problem" in html
    assert message in html
    assert _classes(app) == []


def test_duplicate_name_is_refused_whatever_the_case(signed_in_client, own_class):
    html = signed_in_client.post("/classes/new", data=VALID | {"name": "ce-a"}).get_data(
        as_text=True
    )
    assert "You already have a class with this name" in html


def test_another_mentor_may_use_the_same_name(app, signed_in_client, strangers_class):
    signed_in_client.post("/classes/new", data=VALID | {"name": "IT-B"})
    assert len(_classes(app)) == 2


def test_class_cannot_be_created_for_someone_else(app, signed_in_client, mentor):
    signed_in_client.post("/classes/new", data=VALID | {"mentor_id": "999", "midsem_max": "5"})
    [class_group] = _classes(app)
    assert class_group.mentor_id == mentor.id
    assert class_group.midsem_max == 20


def test_another_mentors_class_is_not_found(signed_in_client, strangers_class):
    assert signed_in_client.get(f"/classes/{strangers_class}").status_code == 404


def test_navigation_lists_classes_and_marks_the_open_one(signed_in_client, own_class):
    html = signed_in_client.get(f"/classes/{own_class}").get_data(as_text=True)
    assert "nav-pane__link--in-section" in html
    assert re.search(rf'href="/classes/{own_class}"\s+aria-current="page"', html)


def test_class_names_are_escaped(app, signed_in_client, mentor):
    with app.app_context():
        class_id = make_class(mentor, name="<b>CE</b>").id
    html = signed_in_client.get(f"/classes/{class_id}").get_data(as_text=True)
    assert "<b>CE</b>" not in html
    assert "&lt;b&gt;CE&lt;/b&gt;" in html
