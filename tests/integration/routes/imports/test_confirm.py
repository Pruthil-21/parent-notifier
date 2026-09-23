import io
import re
from pathlib import Path

import pytest
from sqlalchemy import func, select

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import Student
from tests.factories.academics import make_class, make_semester, make_student
from tests.factories.accounts import make_mentor
from tests.factories.workbooks import make_xlsx


@pytest.fixture
def base(app, mentor):
    with app.app_context():
        class_group = make_class(mentor)
        make_semester(class_group, 4)
        make_semester(class_group, 5)
        return f"/classes/{class_group.id}/sem/4"


def _review(client, base, content=None):
    data = {"sheet": (io.BytesIO(content or make_xlsx()), "sem4.xlsx")}
    html = client.post(f"{base}/import", data=data, content_type="multipart/form-data").get_data(
        as_text=True
    )
    match = re.search(r'name="token" value="([0-9a-f]{32})"', html)
    return html, match.group(1) if match else None


def _students(app):
    with app.app_context():
        return db.session.scalar(select(func.count()).select_from(Student))


def test_confirm_saves_the_sheet_and_reports(app, signed_in_client, base):
    _, token = _review(signed_in_client, base)
    response = signed_in_client.post(f"{base}/import/confirm", data={"token": token})
    assert response.headers["Location"] == base
    html = signed_in_client.get(base).get_data(as_text=True)
    assert "Sheet imported: 2 new and 0 existing students." in html
    assert "Sem 4 sheet imported" in html
    assert "2 students and 2 subjects" in html
    assert _students(app) == 2
    assert list((Path(app.instance_path) / "imports").glob("*.json")) == []


def test_confirming_twice_saves_once(app, signed_in_client, base):
    _, token = _review(signed_in_client, base)
    signed_in_client.post(f"{base}/import/confirm", data={"token": token})
    response = signed_in_client.post(
        f"{base}/import/confirm", data={"token": token}, follow_redirects=True
    )
    assert "This review has expired, so nothing was saved." in response.get_data(as_text=True)
    assert _students(app) == 2


@pytest.mark.parametrize("token", ["", "0" * 32, "../../secret_key"])
def test_unknown_tokens_save_nothing(app, signed_in_client, base, token):
    response = signed_in_client.post(
        f"{base}/import/confirm", data={"token": token}, follow_redirects=True
    )
    assert "This review has expired" in response.get_data(as_text=True)
    assert _students(app) == 0


def test_a_review_cannot_be_confirmed_into_another_semester(app, signed_in_client, base):
    _, token = _review(signed_in_client, base)
    other = base.replace("/sem/4", "/sem/5")
    signed_in_client.post(f"{other}/import/confirm", data={"token": token})
    assert _students(app) == 0


def test_another_mentor_cannot_confirm_a_review(app, signed_in_client, base):
    _, token = _review(signed_in_client, base)
    with app.app_context():
        stranger = make_mentor(username="niravshah", whatsapp_number="+919000000002")
        class_group = make_class(stranger, name="IT-B")
        make_semester(class_group, 4)
        stranger_base = f"/classes/{class_group.id}/sem/4"
    assert (
        signed_in_client.post(f"{stranger_base}/import/confirm", data={"token": token}).status_code
        == 404
    )
    assert _students(app) == 0


def test_identity_differences_are_shown_with_an_unticked_box(app, signed_in_client, base, mentor):
    with app.app_context():
        class_group = make_class(mentor, name="CE-Z")
        make_semester(class_group, 1)
        make_student(class_group, "23CE001", full_name="Avi S", phone_raw="9000000101")
        url = f"/classes/{class_group.id}/sem/1"
    html, _ = _review(signed_in_client, url)
    assert "1 detail differs from what CE-Z holds" in html
    assert "Update these details from the sheet" in html
    assert 'form="confirm-import" id="update_identity"' in html
    assert "checked" not in html


def test_no_box_when_nothing_differs(signed_in_client, base):
    html, _ = _review(signed_in_client, base)
    assert "Update these details from the sheet" not in html
    assert "Confirm import" in html


def test_ticking_the_box_updates_saved_details(app, signed_in_client, mentor):
    with app.app_context():
        class_group = make_class(mentor, name="CE-Z")
        make_semester(class_group, 1)
        make_student(class_group, "23CE001", full_name="Avi S", phone_raw="9000000101")
        url = f"/classes/{class_group.id}/sem/1"
    _, token = _review(signed_in_client, url)
    signed_in_client.post(f"{url}/import/confirm", data={"token": token, "update_identity": "y"})
    with app.app_context():
        student = db.session.scalar(select(Student).where(Student.enrollment_no == "23CE001"))
        assert student.full_name == "Avi Shah"
