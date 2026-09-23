import pytest

from tests.factories.academics import make_class, make_semester
from tests.factories.accounts import make_mentor

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture
def base(app, mentor):
    with app.app_context():
        class_group = make_class(mentor, name="CE-A")
        make_semester(class_group, 4)
        return f"/classes/{class_group.id}/sem/4"


def test_semester_page_links_both_downloads(signed_in_client, base):
    html = signed_in_client.get(base).get_data(as_text=True)
    assert f'href="{base}/sheet.xlsx"' in html
    assert 'href="/sheet-format.xlsx"' in html


def test_sheet_format_download(signed_in_client):
    response = signed_in_client.get("/sheet-format.xlsx")
    assert response.mimetype == XLSX
    assert "parent-notifier-sheet-format.xlsx" in response.headers["Content-Disposition"]
    assert response.data[:2] == b"PK"


def test_prefilled_sheet_download(signed_in_client, base):
    response = signed_in_client.get(f"{base}/sheet.xlsx")
    assert response.mimetype == XLSX
    assert "CE-A-sem-4.xlsx" in response.headers["Content-Disposition"]
    assert response.headers["Cache-Control"] == "no-store"


def test_another_mentors_sheet_is_not_found(app, signed_in_client):
    with app.app_context():
        stranger = make_mentor(username="niravshah", whatsapp_number="+919000000002")
        class_group = make_class(stranger, name="IT-B")
        make_semester(class_group, 4)
        url = f"/classes/{class_group.id}/sem/4/sheet.xlsx"
    assert signed_in_client.get(url).status_code == 404


@pytest.mark.parametrize("path", ["/sheet-format.xlsx", "/classes/1/sem/4/sheet.xlsx"])
def test_downloads_need_sign_in(client, path):
    assert client.get(path).headers["Location"].startswith("/sign-in")
