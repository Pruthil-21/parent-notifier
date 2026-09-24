from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup
from parent_notifier.models.activity import ActivityEntry
from tests.factories.academics import import_sheet, make_class, make_semester
from tests.factories.accounts import make_mentor
from tests.factories.pages import main_content


def test_a_finished_batch_moves_to_past_batches_and_can_reopen(app, signed_in_client, mentor):
    with app.app_context():
        class_group = make_class(mentor, name="CE-OLD", admission_year=2021)
        import_sheet(class_group, make_semester(class_group, 8), mentor.id)
        class_id = class_group.id
    settings = f"/classes/{class_id}/settings"
    assert "At risk" in signed_in_client.get("/").get_data(as_text=True)
    signed_in_client.post(f"{settings}/finish")
    with app.app_context():
        assert db.session.get(ClassGroup, class_id).finished_at is not None
    listing = main_content(signed_in_client.get("/classes/"))
    assert listing.index("Past batches") < listing.index(">CE-OLD<")
    assert ">CE-OLD<" not in main_content(signed_in_client.get("/"))
    assert signed_in_client.get(f"/classes/{class_id}/sem/8").status_code == 200  # still open
    signed_in_client.post(f"{settings}/reopen")
    with app.app_context():
        assert db.session.get(ClassGroup, class_id).finished_at is None
        events = db.session.scalars(db.select(ActivityEntry.event)).all()
    assert "class_finished" in events and "class_reopened" in events


def test_another_mentors_batch_cannot_be_finished(app, signed_in_client):
    with app.app_context():
        stranger = make_mentor(username="niravshah", whatsapp_number="+919000000002")
        class_id = make_class(stranger, name="IT-B").id
    assert signed_in_client.post(f"/classes/{class_id}/settings/finish").status_code == 404
    with app.app_context():
        assert db.session.get(ClassGroup, class_id).finished_at is None
