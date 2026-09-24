from tests.factories.academics import make_class
from tests.factories.accounts import make_mentor


def test_users_list_searches_and_opens_an_account(app, admin_client, mentor):
    with app.app_context():
        make_mentor(full_name="Nirav Shah", username="niravshah", whatsapp_number="+919000000002")
        make_class(mentor, name="CE-B")
    html = admin_client.get("/admin/users/").get_data(as_text=True)
    assert "Asha Patel" in html and "Nirav Shah" in html and "Pruthil Mistry" in html
    found = admin_client.get("/admin/users/?q=nirav").get_data(as_text=True)
    assert "Nirav Shah" in found and "Asha Patel" not in found

    detail = admin_client.get(f"/admin/users/{mentor.id}").get_data(as_text=True)
    assert '<h1 class="page-header__title">Asha Patel</h1>' in detail
    assert "CE-B" in detail and "ashapatel" in detail
    assert admin_client.get("/admin/users/999").status_code == 404
