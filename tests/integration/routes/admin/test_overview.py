from parent_notifier.core.extensions import db
from tests.factories.academics import import_sheet, make_class, make_semester
from tests.factories.accounts import make_mentor
from tests.factories.pages import main_content


def test_the_admin_home_is_the_overview_and_a_mentor_keeps_their_home(app, admin_client, mentor):
    with app.app_context():
        class_group = make_class(mentor, department="Civil Engineering")
        import_sheet(class_group, make_semester(class_group, 4), mentor.id)
    html = main_content(admin_client.get("/"))
    assert '<h1 class="page-header__title">Overview</h1>' in html
    row = html[html.index(">Asha Patel<") :].split("</tr>")[0]
    cells = [cell.strip() for cell in row.split('<td class="numeric">')[1:]]
    assert [cell.split("<")[0] for cell in cells] == ["+91 90000 00001", "1", "4", "1", "4", "0"]

    classes = admin_client.get("/?view=classes").get_data(as_text=True)
    assert ">CE-A<" in classes and "Civil Engineering" in classes and "Sem 4" in classes


def test_search_finds_a_mentor_by_phone_however_it_is_typed(app, admin_client, mentor):
    with app.app_context():
        make_mentor(full_name="Nirav Shah", username="niravshah", whatsapp_number="+919000000002")
    html = main_content(admin_client.get("/?q=90000+00002"))
    assert "Nirav Shah" in html and "Asha Patel" not in html
    assert "Nothing matches" in admin_client.get("/?q=nobody").get_data(as_text=True)


def test_department_filter_and_pages(app, admin_client, mentor):
    with app.app_context():
        for number in range(30):
            make_mentor(
                full_name=f"Mentor {number:02}",
                username=f"mentor{number:02}",
                whatsapp_number=f"+9190000001{number:02}",
                department="Civil Engineering",
            )
        db.session.commit()
    first = main_content(admin_client.get("/?department=civil+engineering"))
    assert "Showing 1&ndash;25 of 30 mentors" in first and "Asha Patel" not in first
    assert '&amp;page=2">Next' in first
    second = admin_client.get("/?department=Civil+Engineering&page=2").get_data(as_text=True)
    assert "Showing 26&ndash;30 of 30 mentors" in second and "Mentor 29" in second
