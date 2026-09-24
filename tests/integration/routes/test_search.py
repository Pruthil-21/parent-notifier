from tests.factories.academics import import_sheet, make_class, make_semester, make_student
from tests.factories.accounts import make_mentor
from tests.factories.pages import main_content


def _search(client, text):
    return main_content(client.get("/search", query_string={"q": text}))


def test_a_mentor_finds_their_own_students_and_classes_only(app, signed_in_client, mentor):
    with app.app_context():
        class_group = make_class(mentor, name="CE-A")
        import_sheet(class_group, make_semester(class_group, 4), mentor.id)
        other = make_mentor(username="nirav", whatsapp_number="+919000000002")
        make_student(make_class(other, name="ME-B"), full_name="Avi Mehta", enrollment_no="23ME009")
        class_id = class_group.id
    by_name = _search(signed_in_client, "avi")
    assert "Avi Shah" in by_name and "Avi Mehta" not in by_name and "ME-B" not in by_name
    assert f"/classes/{class_id}/sem/4/students/" in by_name
    assert "Om Desai" in _search(signed_in_client, "23ce002")
    assert "Riya Patel" in _search(signed_in_client, "90000 00103")  # parent's phone
    assert "CE-A" in _search(signed_in_client, "ce-a")
    assert "Nothing matches" in _search(signed_in_client, "%%")  # not a wildcard
    assert "Type at least 2" in _search(signed_in_client, "a")
    assert "Mentors" not in _search(signed_in_client, "nirav")
