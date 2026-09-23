"""One-time recovery codes: the only way to reset a forgotten password.

Codes are 12 characters from an alphabet without look-alikes (no 0/O, 1/I/L), which is
about 59 bits of randomness. Only a scrypt hash is stored.
"""

import secrets

from parent_notifier.services.accounts.credentials import hash_password

ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LENGTH = 12


def generate() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(LENGTH))


def hash_code(code: str) -> str:
    return hash_password(code)
