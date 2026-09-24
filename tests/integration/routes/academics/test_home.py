import re

import pytest

from tests.factories.academics import import_sheet, make_class, make_semester


def tile(html: str, label: str) -> str:
    """The markup of one home tile, from its link to its end."""
    return re.search(
        rf'<a class="tile__link"[^>]*>\s*<span class="tile__label">{label}</span>.*?</a>',
        html,
        re.S,
    ).group(0)


@pytest.fixture
def one_class(app, mentor):
    with app.app_context():
        class_group = make_class(mentor)
        import_sheet(class_group, make_semester(class_group, 4), mentor.id)
        make_semester(make_class(mentor, name="CE-B"), 1)
        return class_group.id


def test_home_needs_sign_in(client):
    assert client.get("/").status_code == 302


def test_top_bar_shows_the_sending_number_and_account_menu(signed_in_client):
    html = signed_in_client.get("/").get_data(as_text=True)
    assert 'Sending as <span class="numeric">+91 90000 00001</span>' in html
    assert 'aria-label="Account: Asha Patel"' in html
    assert ">AP</span>" in html
    assert 'action="/sign-out"' in html
    assert 'name="csrf_token"' in html


def test_navigation_lists_home_as_current(signed_in_client):
    html = signed_in_client.get("/").get_data(as_text=True)
    assert 'aria-current="page"' in html
    assert '<h1 class="page-header__title">Home</h1>' in html


def test_tiles_open_the_one_class_behind_each_figure(signed_in_client, one_class):
    html = signed_in_client.get("/").get_data(as_text=True)
    at_risk = tile(html, "Students at risk")
    assert f'href="/classes/{one_class}/sem/4?status=at_risk"' in at_risk
    assert 'numeric">1<' in at_risk and "CE-A · Sem 4" in at_risk
    pending = tile(html, "Parents to message")
    assert f'href="/classes/{one_class}/sem/4?status=pending"' in pending
    assert 'numeric">4<' in pending
    assert 'numeric">2<' in tile(html, "Classes") and "4 students now" in html
    waiting = tile(html, "Semesters waiting for a sheet")
    assert re.search(r'href="/classes/\d+/sem/1"', waiting) and "CE-B · Sem 1" in waiting


def test_tiles_point_to_the_class_list_when_several_classes_add_up(
    app, mentor, signed_in_client, one_class
):
    with app.app_context():
        other = make_class(mentor, name="CE-C")
        make_semester(other, 1)  # an older semester that never got its sheet
        import_sheet(other, make_semester(other, 2), mentor.id)
    html = signed_in_client.get("/").get_data(as_text=True)
    assert 'href="#my-classes"' in tile(html, "Students at risk")
    assert "in 2 classes" in tile(html, "Parents to message")
    assert "in 2 classes" in tile(html, "Semesters waiting for a sheet")


def test_my_classes_lists_each_class_with_its_latest_semester(signed_in_client, one_class):
    html = signed_in_client.get("/").get_data(as_text=True)
    grid = html[html.index('id="my-classes"') :]
    assert f'<a href="/classes/{one_class}">CE-A</a>' in grid
    assert grid.index(">CE-A<") < grid.index(">CE-B<")
    assert f'href="/classes/{one_class}/sem/4?status=at_risk"' in grid
    assert 'aria-label="4 pending in CE-A">4</a>' in grid
    assert "Sem 1" in grid and "No sheet yet" in grid


def test_related_links(signed_in_client):
    html = signed_in_client.get("/").get_data(as_text=True)
    assert 'href="/sheet-format.xlsx" download>Download sheet format</a>' in html
    assert 'href="/profile/">Profile</a>' in html
