from datetime import timedelta

from parent_notifier.core.extensions import db
from parent_notifier.models.activity import ActivityEntry
from parent_notifier.services.shared import activity, clock
from tests.factories.accounts import make_mentor


def _seed(app):
    with app.app_context():
        nirav = make_mentor(
            full_name="Nirav Shah",
            username="niravshah",
            whatsapp_number="+919000000002",
            department="Civil Engineering",
        )
        activity.record("security", "sign_in_failed", username="niravshah", succeeded=False)
        activity.record("data", "class_created", actor=nirav, target=("class", 1, "CE-B"))
        old = ActivityEntry(
            category="data", event="class_created", created_at=clock.now() - timedelta(days=500)
        )
        db.session.add(old)
        db.session.commit()


def _rows(html):
    return html.count('<td class="log-when">')


def test_the_log_filters_by_category_person_department_and_failures(app, admin_client):
    _seed(app)
    everything = admin_client.get("/admin/activity/").get_data(as_text=True)
    assert "Sign-in failed" in everything and "Created a class" in everything
    assert "Signed in" in everything  # the admin's own sign-in, logged by the fixture

    data = admin_client.get("/admin/activity/?category=data").get_data(as_text=True)
    assert _rows(data) == 1 and "CE-B" in data and 'name="event"' in data
    by_department = admin_client.get("/admin/activity/?department=Civil+Engineering")
    assert _rows(by_department.get_data(as_text=True)) == 1
    failed = admin_client.get("/admin/activity/?failed=1&person=nirav").get_data(as_text=True)
    assert _rows(failed) == 1 and "Failed</span>" in failed


def test_dates_narrow_the_log_and_old_entries_are_cleared(app, admin_client):
    _seed(app)
    tomorrow = (clock.now() + timedelta(days=1)).date().isoformat()
    later = admin_client.get(f"/admin/activity/?since={tomorrow}").get_data(as_text=True)
    assert "Nothing matches" in later
    with app.app_context():
        oldest = clock.now() - timedelta(days=450)
        remaining = db.session.scalars(
            db.select(ActivityEntry).where(ActivityEntry.created_at < oldest)
        )
        assert list(remaining) == []  # the 500-day-old entry went when the page opened
