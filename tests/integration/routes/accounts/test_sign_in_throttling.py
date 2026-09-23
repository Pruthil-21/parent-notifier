from parent_notifier.core.extensions import db
from parent_notifier.routes.accounts.throttling import FAILURES_PER_ADDRESS, FAILURES_PER_USERNAME
from tests.factories.accounts import PASSWORD, make_mentor, sign_in

LOCKED = "Too many sign-in attempts. Try again in 15 minutes."


def _fail(client, times, username="ashapatel"):
    for _ in range(times):
        assert sign_in(client, username, "wrong-password").status_code == 200


def test_username_is_locked_after_repeated_failures(client, mentor):
    _fail(client, FAILURES_PER_USERNAME)
    response = sign_in(client)
    html = response.get_data(as_text=True)
    assert response.status_code == 429
    assert LOCKED in html
    assert 'value="ashapatel"' in html
    assert client.get("/").status_code == 302


def test_username_counter_ignores_case_and_spaces(client, mentor):
    for username in ("AshaPatel", " ashapatel", "ASHAPATEL ", "ashaPatel", "ashapatel"):
        sign_in(client, username, "wrong-password")
    assert sign_in(client).status_code == 429


def test_failures_below_the_limit_do_not_block_the_right_password(client, mentor):
    _fail(client, FAILURES_PER_USERNAME - 1)
    assert sign_in(client).status_code == 302


def test_forms_with_missing_fields_do_not_count(client, mentor):
    for _ in range(FAILURES_PER_USERNAME + 2):
        sign_in(client, "ashapatel", "")
    assert sign_in(client).status_code == 302


def test_a_locked_username_does_not_lock_other_mentors(app, client, mentor):
    with app.app_context():
        make_mentor(password=PASSWORD, username="niravshah", whatsapp_number="+919000000002")
        db.session.commit()
    _fail(client, FAILURES_PER_USERNAME)
    assert sign_in(client, "niravshah").status_code == 302


def test_one_address_is_locked_after_failures_across_usernames(app, mentor):
    attacker = app.test_client()
    for number in range(FAILURES_PER_ADDRESS):
        sign_in(attacker, f"guess{number}", "wrong-password")
    assert sign_in(attacker, "ashapatel").status_code == 429
    elsewhere = app.test_client()
    elsewhere.environ_base["REMOTE_ADDR"] = "10.0.0.7"
    assert sign_in(elsewhere).status_code == 302


def test_viewing_the_page_is_never_throttled(client, mentor):
    _fail(client, FAILURES_PER_USERNAME)
    assert client.get("/sign-in").status_code == 200
