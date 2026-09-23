"""One-time recovery codes: the only way to reset a forgotten password.

Codes are 12 characters from an alphabet without look-alikes (no 0/O, 1/I/L), which is
about 59 bits of randomness. Only a scrypt hash is stored.
"""

import re
import secrets

from werkzeug.security import check_password_hash

from parent_notifier.services.accounts.credentials import hash_password, unknown_user_hash

ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LENGTH = 12
_SEPARATORS = re.compile(r"[\s-]")


def generate() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(LENGTH))


def hash_code(code: str) -> str:
    return hash_password(code)


def format_for_display(code: str) -> str:
    """ABCDEFGHJKMN becomes ABCD-EFGH-JKMN, which is easier to copy by hand."""
    return "-".join(code[start : start + 4] for start in range(0, len(code), 4))


def normalise(submitted: str) -> str:
    """Mentors may type the code in lowercase, with or without the hyphens."""
    return _SEPARATORS.sub("", submitted or "").upper()


def verify(stored_hash: str | None, submitted: str) -> bool:
    """Check a typed code against a stored hash. Pass None when there is no mentor; a
    hash is still checked so the time taken does not give that away."""
    # Anything much longer than a code cannot be one; do not spend time normalising it.
    code = normalise((submitted or "")[: LENGTH * 4])
    matches = check_password_hash(stored_hash or unknown_user_hash(), code)
    return stored_hash is not None and matches and len(code) == LENGTH
