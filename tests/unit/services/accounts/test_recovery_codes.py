from werkzeug.security import check_password_hash

from parent_notifier.services.accounts import recovery_codes


def test_codes_are_twelve_characters_without_look_alikes():
    code = recovery_codes.generate()
    assert len(code) == 12
    assert set(code) <= set(recovery_codes.ALPHABET)
    assert not set("0O1IL") & set(recovery_codes.ALPHABET)


def test_codes_do_not_repeat():
    assert len({recovery_codes.generate() for _ in range(200)}) == 200


def test_only_a_scrypt_hash_is_kept():
    code = recovery_codes.generate()
    hashed = recovery_codes.hash_code(code)
    assert hashed.startswith("scrypt:")
    assert code not in hashed
    assert check_password_hash(hashed, code)


def test_codes_are_shown_in_groups_of_four():
    assert recovery_codes.format_for_display("ABCDEFGHJKMN") == "ABCD-EFGH-JKMN"


def test_typed_codes_are_normalised():
    assert recovery_codes.normalise(" abcd-efgh jkmn ") == "ABCDEFGHJKMN"


def test_verify_accepts_the_code_however_it_is_typed():
    stored = recovery_codes.hash_code("ABCDEFGHJKMN")
    for typed in ("ABCDEFGHJKMN", "abcd-efgh-jkmn", "ABCD EFGH JKMN"):
        assert recovery_codes.verify(stored, typed)


def test_verify_refuses_wrong_or_missing_codes():
    stored = recovery_codes.hash_code("ABCDEFGHJKMN")
    assert not recovery_codes.verify(stored, "ABCDEFGHJKMP")
    assert not recovery_codes.verify(stored, "")
    assert not recovery_codes.verify(stored, "A" * 5000)
    assert not recovery_codes.verify(None, "ABCDEFGHJKMN")
