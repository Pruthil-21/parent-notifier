"""Password hashing and checking a username and password together."""

from functools import cache

from sqlalchemy import select
from werkzeug.security import check_password_hash, generate_password_hash

from parent_notifier.core.extensions import db
from parent_notifier.models.accounts import Mentor

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128


def hash_password(password: str) -> str:
    return generate_password_hash(password, method="scrypt")


def normalise_username(username: str) -> str:
    return username.strip().lower()


@cache
def _unknown_user_hash() -> str:
    """Checked when no mentor has the username, so a miss takes as long as a wrong
    password and response times do not reveal which usernames exist."""
    return hash_password("no mentor has this username")


def authenticate(username: str, password: str) -> Mentor | None:
    """Return the mentor only when both parts match. Callers show one generic error."""
    mentor = db.session.scalar(
        select(Mentor).where(Mentor.username == normalise_username(username))
    )
    stored_hash = mentor.password_hash if mentor else _unknown_user_hash()
    # Longer passwords can never have been set, but they still pay for a hash check.
    matches = check_password_hash(stored_hash, password[:MAX_PASSWORD_LENGTH])
    if mentor and matches and len(password) <= MAX_PASSWORD_LENGTH:
        return mentor
    return None
