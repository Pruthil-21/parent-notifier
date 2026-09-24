import re

from tests.factories.academics import make_class, make_semester


def _current(html):
    """Links the menu marks as the current page."""
    menu = html[html.index('<nav id="nav-pane"') : html.index("<main")]
    return re.findall(r'href="([^"]+)"\s+aria-current="page"', menu)


def test_the_admin_menu_groups_mentors_and_their_classes(app, admin_client, mentor):
    with app.app_context():
        class_group = make_class(mentor)
        make_semester(class_group, 4)
        class_id = class_group.id
    account = admin_client.get(f"/admin/users/{mentor.id}").get_data(as_text=True)
    # The admin is in Computer Engineering, the mentor has none: two department groups.
    assert 'id="nav-children-mentors-d-computer-engineering"' in account
    assert 'id="nav-children-mentors-d-no-department"' in account
    assert f'id="nav-children-mentors-m{mentor.id}"' in account  # the mentor, with a class
    assert _current(account) == [f"/admin/users/{mentor.id}"]  # not Admin > Users too
    read_only = admin_client.get(f"/admin/classes/{class_id}/sem/4").get_data(as_text=True)
    assert _current(read_only) == [f"/admin/classes/{class_id}"]
    assert _current(admin_client.get("/admin/users/").get_data(as_text=True)) == ["/admin/users/"]
