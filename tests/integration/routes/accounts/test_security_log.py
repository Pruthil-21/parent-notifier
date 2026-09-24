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


def test_the_lockout_holds_on_a_server_that_saw_none_of_the_failures(app, client, mentor):
    from parent_notifier.core.extensions import limiter

    for _ in range(5):
        client.post("/sign-in", data={"username": "ashapatel", "password": "wrong-password"})
    with app.app_context():
        limiter.reset()  # as a fresh server would start, with no counts in memory
    response = client.post("/sign-in", data={"username": "ashapatel", "password": PASSWORD})
    assert response.status_code == 429
    assert "Too many sign-in attempts. Try again in 15 minutes." in response.get_data(as_text=True)
    assert client.get("/").status_code == 302  # not signed in
