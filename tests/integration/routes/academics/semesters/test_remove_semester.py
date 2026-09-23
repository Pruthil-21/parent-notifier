import pytest

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup
from tests.factories.academics import make_class, make_semester, make_student
from tests.factories.accounts import make_mentor


@pytest.fixture
def class_id(app, mentor):
    with app.app_context():
        class_group = make_class(mentor)
        for number in (3, 4):
            make_semester(class_group, number)
        return class_group.id


@pytest.fixture
def strangers_class_id(app):
    with app.app_context():
        stranger = make_mentor(username="niravshah", whatsapp_number="+919000000002")
        class_group = make_class(stranger, name="IT-B")
        make_semester(class_group, 3)
        return class_group.id


def _numbers(app, class_id):
    with app.app_context():
        return [semester.number for semester in db.session.get(ClassGroup, class_id).semesters]


def _fill(app, class_id, number):
    """Give the semester a student, as an import would."""
    with app.app_context():
        class_group = db.session.get(ClassGroup, class_id)
        semester = next(item for item in class_group.semesters if item.number == number)
        student = make_student(class_group)
        semester.students.append(student)
        db.session.commit()


def test_empty_semester_offers_removal(signed_in_client, class_id):
    html = signed_in_client.get(f"/classes/{class_id}/sem/4").get_data(as_text=True)
    assert "Remove this empty semester" in html
    assert '<dialog id="remove-semester"' in html
    assert f'href="/classes/{class_id}/sem/4/remove"' in html


def test_semester_with_a_sheet_does_not_offer_removal(app, signed_in_client, class_id):
    _fill(app, class_id, 4)
    html = signed_in_client.get(f"/classes/{class_id}/sem/4").get_data(as_text=True)
    assert "Remove this empty semester" not in html
    assert "remove-semester" not in html


def test_removing_goes_back_to_the_latest_remaining(app, signed_in_client, class_id):
    response = signed_in_client.post(f"/classes/{class_id}/sem/4/remove")
    assert response.headers["Location"] == f"/classes/{class_id}"
    followed = signed_in_client.get(f"/classes/{class_id}", follow_redirects=True)
    assert followed.request.path == f"/classes/{class_id}/sem/3"
    assert "Sem 4 removed." in followed.get_data(as_text=True)
    assert _numbers(app, class_id) == [3]


def test_removing_the_last_semester_shows_the_start_panel(app, signed_in_client, class_id):
    signed_in_client.post(f"/classes/{class_id}/sem/4/remove")
    signed_in_client.post(f"/classes/{class_id}/sem/3/remove")
    html = signed_in_client.get(f"/classes/{class_id}").get_data(as_text=True)
    assert "No semesters yet" in html


def test_server_refuses_to_remove_a_semester_with_a_sheet(app, signed_in_client, class_id):
    _fill(app, class_id, 4)
    response = signed_in_client.post(f"/classes/{class_id}/sem/4/remove", follow_redirects=True)
    assert "Sem 4 has a sheet, so it cannot be removed." in response.get_data(as_text=True)
    assert _numbers(app, class_id) == [3, 4]


def test_confirmation_page_works_without_javascript(signed_in_client, class_id):
    html = signed_in_client.get(f"/classes/{class_id}/sem/4/remove").get_data(as_text=True)
    assert "Remove Sem 4?" in html
    assert f'action="/classes/{class_id}/sem/4/remove"' in html
    assert "button--danger" in html


def test_missing_semester_is_not_found(signed_in_client, class_id):
    assert signed_in_client.post(f"/classes/{class_id}/sem/9/remove").status_code == 404


@pytest.mark.parametrize("method", ["get", "post"])
def test_another_mentors_semester_is_not_found(app, signed_in_client, strangers_class_id, method):
    response = getattr(signed_in_client, method)(f"/classes/{strangers_class_id}/sem/3/remove")
    assert response.status_code == 404
    assert _numbers(app, strangers_class_id) == [3]


def test_removal_needs_sign_in(app, client, class_id):
    assert (
        client.post(f"/classes/{class_id}/sem/4/remove").headers["Location"].startswith("/sign-in")
    )
    assert _numbers(app, class_id) == [3, 4]
