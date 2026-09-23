import pytest
from werkzeug.security import check_password_hash

from parent_notifier.services.accounts import registration
from tests.factories.accounts import PASSWORD, make_mentor

pytestmark = pytest.mark.usefixtures("app_context")


def test_new_mentor_is_saved_with_normalised_details_and_hashes():
    mentor, code = registration.create_mentor("Asha Patel", "AshaPatel", "98765 43210", PASSWORD)
    assert mentor.id is not None
    assert mentor.username == "ashapatel"
    assert mentor.whatsapp_number == "+919876543210"
    assert check_password_hash(mentor.password_hash, PASSWORD)
    assert check_password_hash(mentor.recovery_code_hash, code)
    assert code not in mentor.recovery_code_hash


def test_taken_username_is_refused_whatever_the_case():
    make_mentor(username="ashapatel")
    assert registration.username_taken(" AshaPatel ")
    with pytest.raises(registration.UsernameTakenError):
        registration.create_mentor("Asha Shah", "ASHAPATEL", "9876543210", PASSWORD)


def test_free_username_is_not_taken():
    assert not registration.username_taken("niravshah")


def test_invalid_number_is_refused():
    with pytest.raises(ValueError, match="not a valid Indian mobile"):
        registration.create_mentor("Asha Patel", "ashapatel", "12345", PASSWORD)


def test_reset_with_the_right_code_changes_password_and_code():
    mentor, code = registration.create_mentor("Asha Patel", "ashapatel", "9876543210", PASSWORD)
    result = registration.reset_password("AshaPatel", code.lower(), "Brand-new-pass-1")
    assert result is not None
    same_mentor, new_code = result
    assert same_mentor == mentor
    assert check_password_hash(mentor.password_hash, "Brand-new-pass-1")
    assert check_password_hash(mentor.recovery_code_hash, new_code)
    assert not check_password_hash(mentor.recovery_code_hash, code)
    assert mentor.session_version == 2


def test_reset_with_a_wrong_code_or_username_changes_nothing():
    mentor, code = registration.create_mentor("Asha Patel", "ashapatel", "9876543210", PASSWORD)
    assert registration.reset_password("ashapatel", "ABCDEFGHJKMN", "Brand-new-pass-1") is None
    assert registration.reset_password("nobody", code, "Brand-new-pass-1") is None
    assert check_password_hash(mentor.password_hash, PASSWORD)
    assert mentor.session_version == 1


def test_a_used_code_does_not_work_twice():
    _mentor, code = registration.create_mentor("Asha Patel", "ashapatel", "9876543210", PASSWORD)
    assert registration.reset_password("ashapatel", code, "Brand-new-pass-1")
    assert registration.reset_password("ashapatel", code, "Another-pass-22") is None
