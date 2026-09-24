"""Changes a signed-in mentor makes to their own account."""

from sqlalchemy.exc import IntegrityError

from parent_notifier.core.extensions import db
from parent_notifier.models.accounts import Mentor
from parent_notifier.services.accounts import registration
from parent_notifier.services.accounts.credentials import authenticate, normalise_username
from parent_notifier.services.shared.phone import normalise_indian_mobile


def update_details(
    mentor: Mentor, full_name: str, username: str, whatsapp_number: str, department: str
) -> None:
    """Save name, username, number and department, all already validated by the form."""
    e164 = normalise_indian_mobile(whatsapp_number)
    if e164 is None:
        raise ValueError("The WhatsApp number is not a valid Indian mobile number.")
    mentor.full_name = full_name
    mentor.username = normalise_username(username)
    mentor.whatsapp_number = e164
    mentor.department = department
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise registration.UsernameTakenError(username) from None


def change_password(mentor: Mentor, current_password: str, new_password: str) -> bool:
    """Set a new password when the current one is right. Other browsers are signed out;
    the caller starts a fresh session for this one."""
    if authenticate(mentor.username, current_password) != mentor:
        return False
    registration.set_password(mentor, new_password)
    db.session.commit()
    return True


def regenerate_recovery_code(mentor: Mentor, current_password: str) -> str | None:
    """Replace the recovery code when the password is right; the old code stops working.
    Asking for the password stops someone at an unlocked computer from making a code
    they could later use to take over the account."""
    if authenticate(mentor.username, current_password) != mentor:
        return None
    code = registration.rotate_recovery_code(mentor)
    db.session.commit()
    return code


def update_preferences(mentor: Mentor, theme: str, message_language: str) -> None:
    mentor.theme = theme
    mentor.message_language = message_language
    db.session.commit()


def update_theme(mentor: Mentor, theme: str) -> None:
    mentor.theme = theme
    db.session.commit()


def update_sending_safety(mentor: Mentor, settings: dict[str, int]) -> None:
    """Gap, burst size, burst pause and daily limit, already range-checked by the form."""
    for name in ("send_gap_seconds", "burst_size", "burst_pause_minutes", "daily_send_limit"):
        setattr(mentor, name, settings[name])
    db.session.commit()
