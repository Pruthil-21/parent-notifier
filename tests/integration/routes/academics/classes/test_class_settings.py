import pytest

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup
from tests.factories.academics import make_class
from tests.factories.accounts import make_mentor

DETAILS = {"name": "CE-A2", "department": "Information Technology", "admission_year": "2024"}
RULES = {"attendance_threshold": "80", "midsem_max": "30", "midsem_pass_mark": "12"}


@pytest.fixture
def class_id(app, mentor):
    with app.app_context():
        return make_class(mentor).id


@pytest.fixture
def strangers_class_id(app):
    with app.app_context():
        stranger = make_mentor(username="niravshah", whatsapp_number="+919000000002")
        return make_class(stranger, name="IT-B").id


def _saved(app, class_id):
    with app.app_context():
        return db.session.get(ClassGroup, class_id)


def test_settings_show_current_details_and_rules(signed_in_client, class_id):
    html = signed_in_client.get(f"/classes/{class_id}/settings/").get_data(as_text=True)
    assert 'value="CE-A"' in html
    assert 'value="Computer Engineering"' in html
    assert 'value="75"' in html
    assert 'value="7"' in html
    assert 'value="20"' in html
    assert html.count('name="csrf_token"') == 6


def test_class_pages_and_list_link_to_settings(signed_in_client, class_id):
    settings_link = f'href="/classes/{class_id}/settings/"'
    assert settings_link in signed_in_client.get(f"/classes/{class_id}").get_data(as_text=True)
    assert settings_link in signed_in_client.get("/classes/").get_data(as_text=True)


def test_saving_details(app, signed_in_client, class_id):
    response = signed_in_client.post(
        f"/classes/{class_id}/settings/details", data=DETAILS, follow_redirects=True
    )
    assert "Class details saved." in response.get_data(as_text=True)
    saved = _saved(app, class_id)
    assert (saved.name, saved.department, saved.admission_year) == (
        "CE-A2",
        "Information Technology",
        2024,
    )


def test_a_class_may_keep_its_own_name(signed_in_client, class_id):
    data = DETAILS | {"name": "ce-a"}
    response = signed_in_client.post(f"/classes/{class_id}/settings/details", data=data)
    assert response.status_code == 302


def test_name_of_another_own_class_is_refused(app, signed_in_client, mentor, class_id):
    with app.app_context():
        make_class(mentor, name="CE-B")
    data = DETAILS | {"name": "CE-B"}
    html = signed_in_client.post(f"/classes/{class_id}/settings/details", data=data).get_data(
        as_text=True
    )
    assert "You already have a class with this name" in html
    assert _saved(app, class_id).name == "CE-A"


def test_saving_rules(app, signed_in_client, class_id):
    response = signed_in_client.post(
        f"/classes/{class_id}/settings/rules", data=RULES, follow_redirects=True
    )
    assert "Status rules saved." in response.get_data(as_text=True)
    saved = _saved(app, class_id)
    assert (saved.attendance_threshold, saved.midsem_max, saved.midsem_pass_mark) == (80, 30, 12)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("attendance_threshold", "", "Enter the minimum attendance"),
        ("attendance_threshold", "0", "Minimum attendance must be from 1 to 100"),
        ("attendance_threshold", "101", "Minimum attendance must be from 1 to 100"),
        ("attendance_threshold", "75%", "Enter the minimum attendance as a whole number"),
        ("midsem_max", "0", "Mid-Sem total must be from 1 to 100"),
        ("midsem_pass_mark", "-1", "Pass mark must be from 0 to 100"),
        ("midsem_pass_mark", "31", "Pass mark cannot be more than the Mid-Sem total of 30"),
    ],
)
def test_invalid_rules_are_explained_and_not_saved(
    app, signed_in_client, class_id, field, value, message
):
    data = RULES | {field: value}
    html = signed_in_client.post(f"/classes/{class_id}/settings/rules", data=data).get_data(
        as_text=True
    )
    assert "There is a problem" in html
    assert message in html
    assert _saved(app, class_id).attendance_threshold == 75


def test_forms_cannot_move_a_class_to_another_mentor(app, signed_in_client, mentor, class_id):
    data = DETAILS | {"mentor_id": "999"}
    signed_in_client.post(f"/classes/{class_id}/settings/details", data=data)
    assert _saved(app, class_id).mentor_id == mentor.id


@pytest.mark.parametrize(
    ("method", "path", "data"),
    [("get", "", None), ("post", "details", DETAILS), ("post", "rules", RULES)],
)
def test_another_mentors_class_is_not_found(
    app, signed_in_client, strangers_class_id, method, path, data
):
    response = getattr(signed_in_client, method)(
        f"/classes/{strangers_class_id}/settings/{path}", data=data
    )
    assert response.status_code == 404
    assert _saved(app, strangers_class_id).name == "IT-B"


def test_settings_need_sign_in(client, class_id):
    response = client.get(f"/classes/{class_id}/settings/")
    assert response.headers["Location"].startswith("/sign-in")
