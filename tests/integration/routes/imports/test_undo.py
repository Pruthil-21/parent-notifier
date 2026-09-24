import io
import re

import pytest
from sqlalchemy import func, select

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import Student
from tests.factories.academics import make_class, make_semester
from tests.factories.accounts import make_mentor
from tests.factories.workbooks import make_xlsx


@pytest.fixture
def base(app, mentor):
    with app.app_context():
        class_group = make_class(mentor)
        make_semester(class_group, 4)
        return f"/classes/{class_group.id}/sem/4"


def _import(client, base):
    data = {"sheet": (io.BytesIO(make_xlsx()), "sem4.xlsx")}
    html = client.post(f"{base}/import", data=data, content_type="multipart/form-data").get_data(
        as_text=True
    )
    token = re.search(r'name="token" value="([0-9a-f]{32})"', html).group(1)
    client.post(f"{base}/import/confirm", data={"token": token})


def _students(app):
    with app.app_context():
        return db.session.scalar(select(func.count()).select_from(Student))


def test_undo_is_offered_only_once_there_is_an_import(signed_in_client, base):
    html = signed_in_client.get(base).get_data(as_text=True)
    assert "Undo last import" not in html
    assert '<dialog id="undo-import"' not in html


def test_after_an_import_undo_explains_what_it_does(signed_in_client, base):
    _import(signed_in_client, base)
    html = signed_in_client.get(base).get_data(as_text=True)
    assert 'data-dialog-open="undo-import"' in html
    assert "sem4.xlsx" in html
    assert "2 added, 0 updated" in html
    page = signed_in_client.get(f"{base}/import/undo").get_data(as_text=True)
    assert "Undo last import?" in page
    assert "upload the same sheet again" in page


def test_undo_restores_the_semester(app, signed_in_client, base):
    _import(signed_in_client, base)
    response = signed_in_client.post(f"{base}/import/undo", follow_redirects=True)
    html = response.get_data(as_text=True)
    assert "Import of sem4.xlsx undone. Sem 4 is back as it was." in html
    assert "No sheet for Sem 4 yet" in html
    assert _students(app) == 0


def test_undo_twice_is_refused(signed_in_client, base):
    _import(signed_in_client, base)
    signed_in_client.post(f"{base}/import/undo")
    response = signed_in_client.post(f"{base}/import/undo", follow_redirects=True)
    assert "There is no import to undo for this semester." in response.get_data(as_text=True)


def test_another_mentors_import_cannot_be_undone(app, signed_in_client, base):
    _import(signed_in_client, base)
    signed_in_client.post("/sign-out")
    with app.app_context():
        make_mentor(username="niravshah", whatsapp_number="+919000000002", password="Other-pass-99")
    signed_in_client.post("/sign-in", data={"username": "niravshah", "password": "Other-pass-99"})
    assert signed_in_client.post(f"{base}/import/undo").status_code == 404
    assert signed_in_client.get(f"{base}/import/undo").status_code == 404
    assert _students(app) == 2


def test_undo_needs_sign_in(app, client, base):
    assert client.post(f"{base}/import/undo").headers["Location"].startswith("/sign-in")
