"""Creating mentor accounts, replacing recovery codes and resetting passwords."""

import secrets

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError

from parent_notifier.core.extensions import db
from parent_notifier.models.accounts import Mentor
from parent_notifier.services.accounts import recovery_codes
from parent_notifier.services.accounts.credentials import hash_password, normalise_username
from parent_notifier.services.shared import clock, settings
from parent_notifier.services.shared.phone import normalise_indian_mobile


class UsernameTakenError(Exception):
    """Another mentor already has this username."""


def username_taken(username: str, except_mentor_id: int | None = None) -> bool:
    """Whether another mentor has this username; a mentor's own username never counts."""
    query = exists().where(
        Mentor.username == normalise_username(username), Mentor.id != (except_mentor_id or 0)
    )
    return db.session.scalar(select(query))


# Who may create an account: nobody but the admin, anyone who is then approved, or anyone.
SIGNUP_OFF, SIGNUP_APPROVAL, SIGNUP_OPEN = "off", "approval", "open"
SIGNUP_MODES = (SIGNUP_OFF, SIGNUP_APPROVAL, SIGNUP_OPEN)
_SIGNUP_KEY = "signup_mode"


def signup_mode() -> str:
    mode = settings.get(_SIGNUP_KEY, SIGNUP_OFF)
    return mode if mode in SIGNUP_MODES else SIGNUP_OFF


def set_signup_mode(mode: str) -> None:
    if mode not in SIGNUP_MODES:
        raise ValueError(f"Unknown sign-up mode {mode!r}")
    settings.put(_SIGNUP_KEY, mode)


def create_mentor(
    full_name: str,
    username: str,
    whatsapp_number: str,
    password: str,
    department: str | None = None,
    **fields,
) -> tuple[Mentor, str]:
    """Save a new mentor and return it with the plain recovery code, which is shown once
    and never stored. The number must already have passed normalise_indian_mobile()."""
    e164 = normalise_indian_mobile(whatsapp_number)
    if e164 is None:
        raise ValueError("The WhatsApp number is not a valid Indian mobile number.")
    code = recovery_codes.generate()
    # An account that cannot sign in yet gets its recovery code at its first sign-in.
    code_hash = recovery_codes.hash_code(code) if fields.get("approved", True) else ""
    mentor = Mentor(
        full_name=full_name,
        username=normalise_username(username),
        whatsapp_number=e164,
        password_hash=hash_password(password),
        recovery_code_hash=code_hash,
        department=department,
        **fields,
    )
    db.session.add(mentor)
    try:
        db.session.commit()
    except IntegrityError:
        # Two people chose the same username at the same moment; the unique index decides.
        db.session.rollback()
        raise UsernameTakenError(username) from None
    return mentor, code


def rotate_recovery_code(mentor: Mentor) -> str:
    """Give the mentor a new code; the old one stops working. The caller commits."""
    code = recovery_codes.generate()
    mentor.recovery_code_hash = recovery_codes.hash_code(code)
    return code


def set_password(mentor: Mentor, password: str) -> None:
    """Store a new password and sign the mentor out of every other browser. The caller
    commits and starts a fresh session for the browser that made the change."""
    mentor.password_hash = hash_password(password)
    mentor.session_version += 1


def reset_password(username: str, code: str, new_password: str) -> tuple[Mentor, str] | None:
    """Reset with a recovery code. Returns the mentor and their new code, or None when
    the username and code do not match (callers show one generic error)."""
    mentor = db.session.scalar(
        select(Mentor).where(Mentor.username == normalise_username(username))
    )
    if not recovery_codes.verify(mentor.recovery_code_hash if mentor else None, code):
        return None
    set_password(mentor, new_password)
    new_code = rotate_recovery_code(mentor)
    db.session.commit()
    return mentor, new_code


def record_sign_in(mentor: Mentor) -> str | None:
    """Note the sign-in. An account that has no recovery code yet (a request the admin
    approved) gets one now, returned so it can be shown once."""
    mentor.last_sign_in_at = clock.now()
    code = None
    # A mentor with an admin-set password gets their code after choosing their own.
    if not mentor.recovery_code_hash and not mentor.must_change_password:
        code = recovery_codes.generate()
        mentor.recovery_code_hash = recovery_codes.hash_code(code)
    db.session.commit()
    return code


# No 0/O or 1/I/L, so a password read out or copied by hand is not mistyped.
_TEMPORARY_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"


def set_temporary_password(mentor: Mentor) -> str:
    """Give the mentor a password chosen by the admin, returned once to be handed over.
    It works for one sign-in: the mentor must then choose their own, and gets a new
    recovery code. Every browser the mentor was signed in on is signed out."""
    groups = ("".join(secrets.choice(_TEMPORARY_ALPHABET) for _ in range(4)) for _ in range(3))
    password = "-".join(groups)
    set_password(mentor, password)
    mentor.must_change_password = True
    mentor.recovery_code_hash = ""
    db.session.commit()
    return password


def choose_own_password(mentor: Mentor, password: str) -> str:
    """Replace an admin-set password with the mentor's own; returns their new recovery
    code, shown once."""
    set_password(mentor, password)
    mentor.must_change_password = False
    code = recovery_codes.generate()
    mentor.recovery_code_hash = recovery_codes.hash_code(code)
    db.session.commit()
    return code
