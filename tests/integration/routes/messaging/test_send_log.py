import io
import re
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import select

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import Semester, Student
from parent_notifier.models.messaging import SendLog
from parent_notifier.services.imports.apply import apply_import
from parent_notifier.services.imports.sheet_parser import parse_sheet
from tests.factories.academics import make_class, make_semester
from tests.factories.accounts import make_mentor
from tests.factories.workbooks import make_xlsx

HEADER = ["Enrollment No", "Student Name", "Parent Name", "Parent Phone", "DBMS"]
ROWS = [
    ["23CE001", "Avi Shah", "Mehul Shah", "9000000101", "Theory=86,Marks=16"],
    ["23CE002", "Riya Patel", "Kiran Patel", "123", "Theory=70"],
]


@pytest.fixture
def setup(app, mentor):
    with app.app_context():
        class_group = make_class(mentor)
        semester = make_semester(class_group, 4)
        apply_import(class_group, semester, mentor.id, "s", parse_sheet([HEADER, *ROWS], 20), False)
        ids = {s.enrollment_no: s.id for s in semester.students}
        return f"/classes/{class_group.id}/sem/4", ids


def _log(client, base, student_id, **body):
    payload = {"status": "sent", "language": "en", "note": ""} | body
    return client.post(f"{base}/students/{student_id}/log", json=payload)


def _entries(app):
    with app.app_context():
        return db.session.scalars(select(SendLog)).all()


def test_send_is_stored_and_returns_the_whatsapp_link(app, signed_in_client, setup):
    base, ids = setup
    response = _log(signed_in_client, base, ids["23CE001"], language="gu")
    data = response.get_json()
    assert response.status_code == 200
    assert data["status"] == "sent"
    assert data["label"].startswith("Sent ")
    query = parse_qs(urlsplit(data["whatsappUrl"]).query)
    assert query["phone"] == ["919000000101"]
    [entry] = _entries(app)
    assert query["text"] == [entry.message]
    assert entry.message.startswith("આદરણીય વાલીશ્રી,")
    assert (entry.round, entry.language) == (1, "gu")


def test_skip_is_stored_without_a_link(app, signed_in_client, setup):
    base, ids = setup
    data = _log(signed_in_client, base, ids["23CE002"], status="skipped").get_json()
    assert (data["status"], data["whatsappUrl"], data["label"]) == ("skipped", None, "Skipped")


@pytest.mark.parametrize(
    "body",
    [{"status": "deleted"}, {"language": "hi"}, {"note": "x" * 501}, {"note": "a\u0000b"}],
)
def test_bad_requests_are_refused(app, signed_in_client, setup, body):
    base, ids = setup
    assert _log(signed_in_client, base, ids["23CE001"], **body).status_code == 400
    assert _entries(app) == []


def test_a_parent_without_a_valid_number_cannot_be_sent(app, signed_in_client, setup):
    base, ids = setup
    response = _log(signed_in_client, base, ids["23CE002"])
    assert response.status_code == 400
    assert "no valid mobile number" in response.get_json()["error"]


def test_left_students_and_other_mentors_are_not_found(app, signed_in_client, setup):
    base, ids = setup
    with app.app_context():
        db.session.get(Student, ids["23CE001"]).status = "left"
        stranger = make_mentor(username="niravshah", whatsapp_number="+919000000002")
        other = make_class(stranger, name="IT-B")
        make_semester(other, 4)
        db.session.commit()
        other_base = f"/classes/{other.id}/sem/4"
    assert _log(signed_in_client, base, ids["23CE001"]).status_code == 404
    assert _log(signed_in_client, other_base, ids["23CE002"]).status_code == 404


def test_log_needs_the_csrf_header(app, mentor, setup):
    base, ids = setup
    app.config["WTF_CSRF_ENABLED"] = True
    client = app.test_client()
    page = client.get("/sign-in").get_data(as_text=True)
    token = re.search(r'name="csrf-token" content="([^"]+)"', page).group(1)
    client.post(
        "/sign-in",
        data={"username": "ashapatel", "password": "Winter-lecture-42", "csrf_token": token},
    )
    # Signing in starts a fresh session, so the page after it carries a new token.
    page = client.get(base).get_data(as_text=True)
    token = re.search(r'name="csrf-token" content="([^"]+)"', page).group(1)
    url = f"{base}/students/{ids['23CE001']}/log"
    body = {"status": "sent", "language": "en", "note": ""}
    assert client.post(url, json=body).status_code == 400
    assert client.post(url, json=body, headers={"X-CSRFToken": token}).status_code == 200


def test_grid_shows_pending_then_sent_and_counts_the_tile(signed_in_client, setup):
    base, ids = setup
    html = signed_in_client.get(base).get_data(as_text=True)
    assert f'data-message-cell="{ids["23CE001"]}" class="text-secondary">Pending' in html
    assert f'data-message-cell="{ids["23CE002"]}" class="text-secondary">No phone' in html
    _log(signed_in_client, base, ids["23CE001"])
    html = signed_in_client.get(base).get_data(as_text=True)
    assert f'data-message-cell="{ids["23CE001"]}" class="message-done">Sent' in html
    tile = r'Parents messaged</span>\s*<span class="tile__value numeric">1 <span class="tile__of">'
    assert re.search(tile + "of 1", html)


def test_new_import_makes_parents_pending_and_undo_brings_marks_back(app, signed_in_client, setup):
    base, ids = setup
    _log(signed_in_client, base, ids["23CE001"])
    data = {"sheet": (io.BytesIO(make_xlsx([HEADER, *ROWS])), "again.xlsx")}
    html = signed_in_client.post(
        f"{base}/import", data=data, content_type="multipart/form-data"
    ).get_data(as_text=True)
    token = re.search(r'name="token" value="([0-9a-f]{32})"', html).group(1)
    signed_in_client.post(f"{base}/import/confirm", data={"token": token})
    assert (
        ">Pending<"
        in signed_in_client.get(base)
        .get_data(as_text=True)
        .split(f'data-message-cell="{ids["23CE001"]}"')[1][:40]
    )
    signed_in_client.post(f"{base}/import/undo")
    after = signed_in_client.get(base).get_data(as_text=True)
    assert after.split(f'data-message-cell="{ids["23CE001"]}"')[1].startswith(
        ' class="message-done">Sent'
    )
    with app.app_context():
        assert db.session.scalar(select(Semester)).current_round == 1
