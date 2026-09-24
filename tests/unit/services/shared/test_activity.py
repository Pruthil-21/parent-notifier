import pytest

from parent_notifier.core.extensions import db
from parent_notifier.models.activity import ActivityEntry
from parent_notifier.services.shared import activity
from tests.factories.academics import make_class, make_student
from tests.factories.accounts import make_mentor

pytestmark = pytest.mark.usefixtures("app_context")


def _entries():
    return list(db.session.scalars(db.select(ActivityEntry).order_by(ActivityEntry.id)))


def test_an_entry_copies_who_did_it_and_what_it_was_done_to():
    mentor = make_mentor(department="Civil Engineering")
    class_group = make_class(mentor)
    student = make_student(class_group)
    activity.record(
        "data", "student_deleted", actor=mentor, target=student, class_group=class_group
    )
    [entry] = _entries()
    assert (entry.actor_name, entry.username, entry.department) == (
        "Asha Patel",
        "ashapatel",
        "Civil Engineering",
    )
    assert (entry.target_type, entry.target_label, entry.class_label) == (
        "student",
        "Avi Shah (23CE001)",
        "CE-A",
    )
    db.session.delete(mentor)
    db.session.commit()
    db.session.refresh(entry)
    assert (entry.actor_id, entry.actor_name) == (None, "Asha Patel")  # still readable


def test_a_failed_sign_in_keeps_only_the_typed_username():
    activity.record("security", "sign_in_failed", username="x" * 40, succeeded=False)
    [entry] = _entries()
    assert (entry.actor_id, entry.username, entry.succeeded) == (None, "x" * 30, False)


def test_every_event_has_a_name_and_unknown_events_are_refused():
    assert activity.event_label("admin", "classes_transferred") == "Transferred classes"
    with pytest.raises(ValueError, match="Unknown activity"):
        activity.record("data", "made_up")
