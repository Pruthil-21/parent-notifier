import io

import pytest
from sqlalchemy import func, select

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import Student
from parent_notifier.models.imports import StagedSheet
from tests.factories.academics import make_class, make_semester
from tests.factories.accounts import make_mentor
from tests.factories.workbooks import make_csv, make_xlsx, sheet_rows


@pytest.fixture
def base(app, mentor):
    with app.app_context():
        class_group = make_class(mentor)
        make_semester(class_group, 4)
        return f"/classes/{class_group.id}/sem/4"


@pytest.fixture
def strangers_base(app):
    with app.app_context():
        stranger = make_mentor(username="niravshah", whatsapp_number="+919000000002")
        class_group = make_class(stranger, name="IT-B")
        make_semester(class_group, 4)
        return f"/classes/{class_group.id}/sem/4"


def _upload(client, base, content=None, filename="sem4.xlsx"):
    data = {"sheet": (io.BytesIO(content or make_xlsx()), filename)}
    return client.post(f"{base}/import", data=data, content_type="multipart/form-data")


def _staged(app):
    with app.app_context():
        return list(db.session.scalars(select(StagedSheet.token)))


def _students(app):
    with app.app_context():
        return db.session.scalar(select(func.count()).select_from(Student))


def test_semester_page_offers_upload(signed_in_client, base):
    html = signed_in_client.get(base).get_data(as_text=True)
    assert 'data-dialog-open="upload-sheet"' in html
    assert '<dialog id="upload-sheet"' in html
    assert 'enctype="multipart/form-data"' in html


def test_upload_page_works_without_javascript(signed_in_client, base):
    html = signed_in_client.get(f"{base}/upload").get_data(as_text=True)
    assert 'accept=".xlsx,.csv"' in html


def test_good_sheet_is_reviewed_and_staged_but_not_saved(app, signed_in_client, base):
    html = _upload(signed_in_client, base).get_data(as_text=True)
    assert "Review Sem 4 sheet" in html
    assert "Nothing is saved until you confirm." in html
    assert "sem4.xlsx" in html
    assert "DBMS, OS" in html
    assert "86 / 92 / 16" in html
    assert '79 / <span class="text-muted">\u2013</span> / AB' in html
    assert len(_staged(app)) == 1
    assert _students(app) == 0


def test_csv_is_accepted(app, signed_in_client, base):
    response = _upload(signed_in_client, base, make_csv(), "sem4.csv")
    assert "Review Sem 4 sheet" in response.get_data(as_text=True)


def test_sheet_with_errors_lists_them_and_stages_nothing(app, signed_in_client, base):
    rows = sheet_rows(rows=[["23CE001", "Avi Shah", "Mehul Shah", "9000000101", "Theory=120", ""]])
    html = _upload(signed_in_client, base, make_xlsx(rows)).get_data(as_text=True)
    assert "Fix 1 problem in the sheet, then upload it again" in html
    assert "Row 2, DBMS: Theory must be a percentage from 0 to 100" in html
    assert "Upload the fixed sheet" in html
    assert _staged(app) == []


def test_warnings_and_ignored_columns_are_shown(signed_in_client, base):
    rows = [["Sr No", *sheet_rows()[0]], ["1", "23CE001", "Avi", "Mehul", "123", "Theory=80", ""]]
    html = _upload(signed_in_client, base, make_xlsx(rows)).get_data(as_text=True)
    assert "will be ignored: Sr No" in html
    assert "parent phone is &#34;123&#34;" in html


@pytest.mark.parametrize(
    ("filename", "content", "message"),
    [
        ("marks.pdf", b"%PDF", "Upload an Excel (.xlsx) or CSV (.csv) file"),
        ("marks.xls", b"old", "Save old .xls files as .xlsx first"),
        ("sem4.xlsx", b"not really a workbook", "The file could not be read"),
    ],
)
def test_unusable_files_are_explained(app, signed_in_client, base, filename, content, message):
    html = _upload(signed_in_client, base, content, filename).get_data(as_text=True)
    assert "There is a problem" in html
    assert message in html
    assert _staged(app) == []


def test_missing_file_is_explained(signed_in_client, base):
    html = signed_in_client.post(f"{base}/import", data={}).get_data(as_text=True)
    assert "Choose the semester&#39;s sheet to upload" in html


def test_sheet_content_is_escaped(signed_in_client, base):
    rows = sheet_rows(rows=[["23CE001", "<script>x</script>", "Mehul", "9000000101", "", ""]])
    html = _upload(signed_in_client, base, make_xlsx(rows)).get_data(as_text=True)
    assert "<script>x</script>" not in html
    assert "&lt;script&gt;x&lt;/script&gt;" in html


def test_cancel_discards_the_staged_sheet(app, signed_in_client, base):
    _upload(signed_in_client, base)
    token = _staged(app)[0]
    response = signed_in_client.post(f"{base}/import/cancel", data={"token": token})
    assert response.headers["Location"] == base
    assert _staged(app) == []
    html = signed_in_client.get(base).get_data(as_text=True)
    assert "Import cancelled. Nothing was saved." in html


@pytest.mark.parametrize("path", ["upload", "import", "import/cancel"])
def test_another_mentors_semester_is_not_found(signed_in_client, strangers_base, path):
    method = signed_in_client.get if path == "upload" else signed_in_client.post
    assert method(f"{strangers_base}/{path}").status_code == 404


def test_upload_needs_sign_in(app, client, base):
    assert _upload(client, base).headers["Location"].startswith("/sign-in")
    assert _staged(app) == []
