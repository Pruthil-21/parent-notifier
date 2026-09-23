import pytest
from werkzeug.security import check_password_hash

from parent_notifier.services.accounts import profile, registration
from tests.factories.accounts import PASSWORD, make_mentor

pytestmark = pytest.mark.usefixtures("app_context")


def test_details_are_saved_normalised():
    mentor = make_mentor()
    profile.update_details(mentor, "Asha R. Patel", "AshaP", "+91 90000 00009")
    assert (mentor.username, mentor.whatsapp_number) == ("ashap", "+919000000009")


def test_a_mentors_own_username_is_not_taken_for_them():
    mentor = make_mentor()
    assert registration.username_taken("ashapatel")
    assert not registration.username_taken("ashapatel", except_mentor_id=mentor.id)


def test_clash_at_save_time_raises_and_keeps_the_old_details():
    make_mentor(username="niravshah", whatsapp_number="+919000000002")
    mentor = make_mentor()
    with pytest.raises(registration.UsernameTakenError):
        profile.update_details(mentor, "Asha Patel", "niravshah", "9000000001")
    assert mentor.username == "ashapatel"


def test_password_changes_only_with_the_current_one():
    mentor = make_mentor(password=PASSWORD)
    assert not profile.change_password(mentor, "not-it", "Brand-new-pass-1")
    assert mentor.session_version == 1
    assert profile.change_password(mentor, PASSWORD, "Brand-new-pass-1")
    assert check_password_hash(mentor.password_hash, "Brand-new-pass-1")
    assert mentor.session_version == 2


def test_recovery_code_is_replaced_only_with_the_current_password():
    mentor = make_mentor(password=PASSWORD)
    before = mentor.recovery_code_hash
    assert profile.regenerate_recovery_code(mentor, "not-it") is None
    assert mentor.recovery_code_hash == before
    code = profile.regenerate_recovery_code(mentor, PASSWORD)
    assert check_password_hash(mentor.recovery_code_hash, code)
    assert mentor.session_version == 1
