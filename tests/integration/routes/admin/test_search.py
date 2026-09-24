from tests.factories.academics import import_sheet, make_class, make_semester
from tests.factories.accounts import make_mentor
from tests.factories.pages import main_content


def _search(client, text):
    return main_content(client.get("/search", query_string={"q": text}))


def test_the_admin_finds_everyone_and_opens_others_read_only(app, admin_client, mentor):
    with app.app_context():
        class_group = make_class(mentor, name="CE-A", department="Civil Engineering")
        import_sheet(class_group, make_semester(class_group, 4), mentor.id)
        make_mentor(
            full_name="Nirav Shah",
            username="niravshah",
            whatsapp_number="+919000000002",
            department="Civil Engineering",
        )
        class_id = class_group.id
    student = _search(admin_client, "om desai")
    assert f"/admin/classes/{class_id}/sem/4/students/" in student
    assert f'href="/admin/classes/{class_id}"' in _search(admin_client, "ce-a")
    by_phone = _search(admin_client, "90000-00001")
    assert "Asha Patel" in by_phone and f"/admin/users/{mentor.id}" in by_phone
    by_department = _search(admin_client, "civil")
    assert "Nirav Shah" in by_department and "CE-A" in by_department
