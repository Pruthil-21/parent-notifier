import pytest

from parent_notifier.services.accounts import credentials
from tests.factories.accounts import PASSWORD, make_mentor

pytestmark = pytest.mark.usefixtures("app_context")


def test_passwords_are_hashed_with_scrypt():
    hashed = credentials.hash_password(PASSWORD)
    assert hashed.startswith("scrypt:")
    assert PASSWORD not in hashed


def test_matching_username_and_password_returns_the_mentor():
    mentor = make_mentor(password=PASSWORD)
    assert credentials.authenticate("ashapatel", PASSWORD) == mentor


def test_username_ignores_case_and_surrounding_spaces():
    mentor = make_mentor(password=PASSWORD)
    assert credentials.authenticate("  AshaPatel ", PASSWORD) == mentor


def test_wrong_password_returns_nothing():
    make_mentor(password=PASSWORD)
    assert credentials.authenticate("ashapatel", PASSWORD.lower()) is None


def test_unknown_username_still_checks_a_hash(monkeypatch):
    checked = []
    real_check = credentials.check_password_hash

    def spy(stored_hash, password):
        checked.append(stored_hash)
        return real_check(stored_hash, password)

    monkeypatch.setattr(credentials, "check_password_hash", spy)
    assert credentials.authenticate("nobody", PASSWORD) is None
    assert len(checked) == 1
    assert checked[0].startswith("scrypt:")


def test_password_longer_than_the_limit_never_matches():
    long_password = "x" * (credentials.MAX_PASSWORD_LENGTH + 1)
    make_mentor(password=long_password[: credentials.MAX_PASSWORD_LENGTH])
    assert credentials.authenticate("ashapatel", long_password) is None
