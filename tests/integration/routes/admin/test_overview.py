import re

from parent_notifier.core.extensions import db
from parent_notifier.services.shared import clock
from tests.factories.academics import import_sheet, make_class, make_semester
from tests.factories.accounts import make_mentor
from tests.factories.pages import main_content


def _tiles(html):
    return dict(
        re.findall(r'tile__label">([^<]+)</span>\s*<span class="tile__value numeric">(\d+)', html)
    )


def test_the_overview_shows_what_needs_attention_in_current_classes(app, admin_client, mentor):
    with app.app_context():
        civil = make_class(mentor, name="CE-A", department="Civil Engineering")
        import_sheet(civil, make_semester(civil, 4), mentor.id)
        old = make_class(mentor, name="CE-OLD", admission_year=2019, finished_at=clock.now())
        import_sheet(old, make_semester(old, 8), mentor.id)
        make_class(mentor, name="IT-A", department="Information Technology")  # no sheet yet
    html = main_content(admin_client.get("/"))
    assert '<h1 class="page-header__title">Overview</h1>' in html
    # The imported class counts; the finished batch does not.
    assert _tiles(html) == {
        "Classes": "2",
        "Students": "4",
        "At risk": "1",
        "Messages pending": "4",
        "Sent, last 7 days": "0",
    }
    assert "Civil Engineering" in html and "Information Technology" in html
    pending = html[html.index('id="pending-heading"') :]
    assert ">CE-A<" in pending and ">IT-A<" not in pending and ">CE-OLD<" not in pending
    it_only = main_content(admin_client.get("/?department=Information+Technology"))
    assert "No messages pending" in it_only


def test_all_classes_filters_sorts_and_pages(app, admin_client, mentor):
    with app.app_context():
        nirav = make_mentor(
            full_name="Nirav Shah", username="niravshah", whatsapp_number="+919000000002"
        )
        for number in range(30):
            make_class(
                nirav, name=f"CV-{number:02}", department="Civil Engineering", admission_year=2024
            )
        busy = make_class(mentor, name="CE-A")
        import_sheet(busy, make_semester(busy, 4), mentor.id)
        make_class(mentor, name="CE-OLD", admission_year=2019, finished_at=clock.now())
        db.session.commit()
    first = main_content(admin_client.get("/admin/classes/?department=civil+engineering"))
    assert "Showing 1&ndash;25 of 30 classes" in first and "CE-A" not in first
    second = main_content(admin_client.get("/admin/classes/?department=Civil+Engineering&page=2"))
    assert "Showing 26&ndash;30 of 30 classes" in second and "CV-29" in second
    by_pending = main_content(admin_client.get("/admin/classes/?sort=pending"))
    assert by_pending.index(">CE-A<") < by_pending.index(">CV-00<")
    assert ">CE-OLD<" not in by_pending
    finished = main_content(admin_client.get("/admin/classes/?status=finished"))
    assert ">CE-OLD<" in finished and ">CE-A<" not in finished
    assert ">CV-05<" in main_content(admin_client.get("/admin/classes/?q=nirav&year=2024"))
