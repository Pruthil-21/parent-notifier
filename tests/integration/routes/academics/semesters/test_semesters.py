import re
from datetime import date

import pytest

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup
from parent_notifier.services.shared import clock
from tests.factories.academics import make_class, make_semester
from tests.factories.accounts import make_mentor


@pytest.fixture(autouse=True)
def september_2026(monkeypatch):
    monkeypatch.setattr(clock, "today", lambda _timezone: date(2026, 9, 23))


@pytest.fixture
def class_id(app, mentor):
    with app.app_context():
        return make_class(mentor, admission_year=2023).id


@pytest.fixture
def strangers_class_id(app):
    with app.app_context():
        stranger = make_mentor(username="niravshah", whatsapp_number="+919000000002")
        class_group = make_class(stranger, name="IT-B")
        make_semester(class_group, 3)
        return class_group.id


def _add_semesters(app, class_id, *numbers):
    with app.app_context():
        class_group = db.session.get(ClassGroup, class_id)
        for number in numbers:
            make_semester(class_group, number)


def _numbers(app, class_id):
    with app.app_context():
        return [semester.number for semester in db.session.get(ClassGroup, class_id).semesters]


def test_class_without_semesters_offers_to_add_one(signed_in_client, class_id):
    html = signed_in_client.get(f"/classes/{class_id}").get_data(as_text=True)
    assert "No semesters yet" in html
    assert re.search(
        rf'data-dialog-open="add-semester"\s+href="/classes/{class_id}/semesters/new"', html
    )
    assert '<dialog id="add-semester"' in html
    assert 'value="7"' in html


def test_adding_a_semester_opens_it(app, signed_in_client, class_id):
    response = signed_in_client.post(f"/classes/{class_id}/semesters", data={"number": "7"})
    assert response.headers["Location"] == f"/classes/{class_id}/sem/7"
    html = signed_in_client.get(response.headers["Location"]).get_data(as_text=True)
    assert "Sem 7 added." in html
    assert "No sheet for Sem 7 yet" in html
    assert _numbers(app, class_id) == [7]


def test_opening_a_class_goes_to_its_latest_semester(app, signed_in_client, class_id):
    _add_semesters(app, class_id, 3, 5)
    response = signed_in_client.get(f"/classes/{class_id}")
    assert response.headers["Location"] == f"/classes/{class_id}/sem/5"


def test_switcher_lists_every_semester_and_suggests_the_next(app, signed_in_client, class_id):
    _add_semesters(app, class_id, 3, 4)
    html = signed_in_client.get(f"/classes/{class_id}/sem/3").get_data(as_text=True)
    assert 'aria-label="Semester: Sem 3. Change semester"' in html
    assert re.search(rf'href="/classes/{class_id}/sem/3"\s+aria-current="page"', html)
    assert f'href="/classes/{class_id}/sem/4"' in html
    assert html.count("No sheet yet") == 2
    assert 'value="5"' in html


def test_adding_an_existing_semester_just_opens_it(app, signed_in_client, class_id):
    signed_in_client.post(f"/classes/{class_id}/semesters", data={"number": "4"})
    response = signed_in_client.post(
        f"/classes/{class_id}/semesters", data={"number": "4"}, follow_redirects=True
    )
    assert "Sem 4 already exists, so it is open now." in response.get_data(as_text=True)
    assert _numbers(app, class_id) == [4]


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("", "Enter the semester number"),
        ("four", "Enter the semester as a number from 1 to 12"),
        ("0", "Semester must be from 1 to 12"),
        ("13", "Semester must be from 1 to 12"),
    ],
)
def test_invalid_numbers_show_the_form_page_with_errors(
    app, signed_in_client, class_id, value, message
):
    response = signed_in_client.post(f"/classes/{class_id}/semesters", data={"number": value})
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "There is a problem" in html
    assert message in html
    assert _numbers(app, class_id) == []


def test_add_page_works_without_javascript(signed_in_client, class_id):
    html = signed_in_client.get(f"/classes/{class_id}/semesters/new").get_data(as_text=True)
    assert '<h1 class="page-header__title">Add semester</h1>' in html
    assert f'action="/classes/{class_id}/semesters"' in html


def test_missing_semester_is_not_found(signed_in_client, class_id):
    assert signed_in_client.get(f"/classes/{class_id}/sem/2").status_code == 404


@pytest.mark.parametrize(
    ("method", "path"),
    [("get", "sem/3"), ("get", "semesters/new"), ("post", "semesters")],
)
def test_another_mentors_class_is_not_found(
    app, signed_in_client, strangers_class_id, method, path
):
    url = f"/classes/{strangers_class_id}/{path}"
    response = getattr(signed_in_client, method)(url, data={"number": "5"})
    assert response.status_code == 404
    assert _numbers(app, strangers_class_id) == [3]


@pytest.mark.parametrize("path", ["sem/1", "semesters/new"])
def test_semester_pages_need_sign_in(client, class_id, path):
    assert client.get(f"/classes/{class_id}/{path}").headers["Location"].startswith("/sign-in")
