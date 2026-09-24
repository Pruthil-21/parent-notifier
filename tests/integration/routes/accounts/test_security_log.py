from parent_notifier.core.extensions import db
from parent_notifier.models.activity import ActivityEntry
from tests.factories.accounts import PASSWORD


def _log(app):
    with app.app_context():
        entries = db.session.scalars(db.select(ActivityEntry).order_by(ActivityEntry.id))
        return [(e.event, e.username, e.succeeded, bool(e.ip_address)) for e in entries]


def test_sign_ins_failures_and_sign_outs_are_logged_with_the_address(app, client, mentor):
    client.post("/sign-in", data={"username": " AshaPatel ", "password": "wrong-password"})
    client.post("/sign-in", data={"username": "ashapatel", "password": PASSWORD})
    client.post("/sign-out")
    assert _log(app) == [
        ("sign_in_failed", "ashapatel", False, True),
        ("sign_in", "ashapatel", True, True),
        ("sign_out", "ashapatel", True, True),
    ]


def test_password_changes_are_logged_but_never_the_password(app, signed_in_client):
    data = {"current_password": PASSWORD, "new_password": "Summer-lecture-43"}
    signed_in_client.post("/profile/password", data=data)
    with app.app_context():
        entry = db.session.scalars(
            db.select(ActivityEntry).filter_by(event="password_changed")
        ).one()
        assert PASSWORD not in str(vars(entry)) and "Summer" not in str(vars(entry))
