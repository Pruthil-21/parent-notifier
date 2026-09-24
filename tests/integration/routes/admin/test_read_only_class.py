import pytest

from tests.factories.academics import import_sheet, make_class, make_semester


@pytest.fixture
def class_id(app, mentor):
    with app.app_context():
        class_group = make_class(mentor)
        import_sheet(class_group, make_semester(class_group, 4), mentor.id)
        return class_group.id


def test_the_admin_sees_a_mentors_class_without_any_way_to_change_it(admin_client, class_id):
    opened = admin_client.get(f"/admin/classes/{class_id}")
    assert opened.headers["Location"] == f"/admin/classes/{class_id}/sem/4"
    html = admin_client.get(f"/admin/classes/{class_id}/sem/4").get_data(as_text=True)
    assert "Viewing Asha Patel's class. It is read-only" in html
    assert 'data-read-only="true"' in html
    for control in (
        "data-popup-send",
        "data-queue-open",
        "data-log-url",
        "data-edit-url",
        "sheet-menu",
        "Add student",
        "Class settings",
        'id="sending-as"',
    ):
        assert control not in html, control
    assert f'href="/admin/classes/{class_id}/sem/4/students/' in html
    assert "Prof. Asha Patel" in html  # messages are signed by the class's mentor


def test_the_admin_still_cannot_change_the_class_through_the_mentor_pages(admin_client, class_id):
    base = f"/classes/{class_id}/sem/4"
    assert admin_client.get(base).status_code == 404
    assert admin_client.post(f"{base}/students/1/log", json={"status": "sent"}).status_code in {
        400,
        404,
    }
    assert (
        admin_client.post(f"/classes/{class_id}/delete", data={"confirmation": "CE-A"}).status_code
        == 404
    )
