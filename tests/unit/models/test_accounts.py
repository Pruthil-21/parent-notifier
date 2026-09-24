import pytest
from sqlalchemy.exc import IntegrityError

from parent_notifier.core.extensions import db
from parent_notifier.models.accounts import load_mentor
from tests.factories.accounts import make_mentor

pytestmark = pytest.mark.usefixtures("app_context")


def test_new_mentor_gets_documented_defaults():
    mentor = make_mentor()
    assert mentor.theme == "system"
    assert (mentor.send_gap_seconds, mentor.burst_size) == (20, 15)
    assert (mentor.burst_pause_minutes, mentor.daily_send_limit) == (5, 60)
    assert mentor.session_version == 1
    assert (mentor.role, mentor.is_admin, mentor.approved) == ("mentor", False, True)
    assert (mentor.department, mentor.must_change_password, mentor.last_sign_in_at) == (
        None,
        False,
        None,
    )


def test_usernames_are_unique():
    make_mentor(username="ashapatel")
    with pytest.raises(IntegrityError):
        make_mentor(username="ashapatel", whatsapp_number="+919000000002")


@pytest.mark.parametrize(
    "fields",
    [{"username": "AshaPatel"}, {"theme": "blue"}, {"role": "hod"}],
    ids=["uppercase username", "unknown theme", "unknown role"],
)
def test_database_rejects_invalid_values(fields):
    with pytest.raises(IntegrityError):
        make_mentor(**fields)
    db.session.rollback()


def test_repr_leaves_out_hashes():
    mentor = make_mentor(password_hash="scrypt:secret-hash")
    assert repr(mentor) == f"<Mentor {mentor.id} ashapatel>"


def test_login_id_carries_the_session_version():
    mentor = make_mentor()
    assert mentor.get_id() == f"{mentor.id}:1"


def test_loader_finds_the_mentor_for_a_current_login_id():
    mentor = make_mentor()
    assert load_mentor(mentor.get_id()) == mentor


def test_loader_rejects_ids_from_before_a_version_bump():
    mentor = make_mentor()
    old_id = mentor.get_id()
    mentor.session_version += 1
    db.session.commit()
    assert load_mentor(old_id) is None


@pytest.mark.parametrize("login_id", ["", "1", "1:", ":1", "abc:1", "1:x", "999:1", "-1:1"])
def test_loader_rejects_malformed_or_unknown_ids(login_id):
    make_mentor()
    assert load_mentor(login_id) is None


@pytest.mark.parametrize(
    ("full_name", "initials"),
    [("Asha Patel", "AP"), ("Pruthil Mistry", "PM"), ("Nirav", "N"), ("asha r. patel", "AP")],
)
def test_initials_use_first_and_last_names(full_name, initials):
    assert make_mentor(full_name=full_name).initials == initials


def test_an_account_waiting_for_approval_cannot_stay_signed_in():
    mentor = make_mentor(approved=False)
    assert load_mentor(mentor.get_id()) is None
    mentor.approved = True
    db.session.commit()
    assert load_mentor(mentor.get_id()) == mentor
