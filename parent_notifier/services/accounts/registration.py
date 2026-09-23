"""Creating mentor accounts."""

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError

from parent_notifier.core.extensions import db
from parent_notifier.models.accounts import Mentor
from parent_notifier.services.accounts import recovery_codes
from parent_notifier.services.accounts.credentials import hash_password, normalise_username
from parent_notifier.services.shared.phone import normalise_indian_mobile


class UsernameTakenError(Exception):
    """Another mentor already has this username."""


def username_taken(username: str) -> bool:
    return db.session.scalar(
        select(exists().where(Mentor.username == normalise_username(username)))
    )


def create_mentor(
    full_name: str, username: str, whatsapp_number: str, password: str
) -> tuple[Mentor, str]:
    """Save a new mentor and return it with the plain recovery code, which is shown once
    and never stored. The number must already have passed normalise_indian_mobile()."""
    e164 = normalise_indian_mobile(whatsapp_number)
    if e164 is None:
        raise ValueError("The WhatsApp number is not a valid Indian mobile number.")
    code = recovery_codes.generate()
    mentor = Mentor(
        full_name=full_name,
        username=normalise_username(username),
        whatsapp_number=e164,
        password_hash=hash_password(password),
        recovery_code_hash=recovery_codes.hash_code(code),
    )
    db.session.add(mentor)
    try:
        db.session.commit()
    except IntegrityError:
        # Two people chose the same username at the same moment; the unique index decides.
        db.session.rollback()
        raise UsernameTakenError(username) from None
    return mentor, code
