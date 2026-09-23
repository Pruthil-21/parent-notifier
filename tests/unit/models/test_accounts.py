import pytest
from sqlalchemy.exc import IntegrityError

from parent_notifier.core.extensions import db
from tests.factories.accounts import make_mentor

pytestmark = pytest.mark.usefixtures("app_context")


def test_new_mentor_gets_documented_defaults():
    mentor = make_mentor()
    assert (mentor.theme, mentor.message_language) == ("system", "en")
    assert (mentor.send_gap_seconds, mentor.burst_size) == (20, 15)
    assert (mentor.burst_pause_minutes, mentor.daily_send_limit) == (5, 60)
    assert mentor.session_version == 1


def test_usernames_are_unique():
    make_mentor(username="ashapatel")
    with pytest.raises(IntegrityError):
        make_mentor(username="ashapatel", whatsapp_number="+919000000002")


@pytest.mark.parametrize(
    "fields",
    [{"username": "AshaPatel"}, {"theme": "blue"}, {"message_language": "hi"}],
    ids=["uppercase username", "unknown theme", "unknown language"],
)
def test_database_rejects_invalid_values(fields):
    with pytest.raises(IntegrityError):
        make_mentor(**fields)
    db.session.rollback()


def test_repr_leaves_out_hashes():
    mentor = make_mentor(password_hash="scrypt:secret-hash")
    assert repr(mentor) == f"<Mentor {mentor.id} ashapatel>"
