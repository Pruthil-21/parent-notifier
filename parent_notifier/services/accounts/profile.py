"""Changes a signed-in mentor makes to their own account."""

from sqlalchemy.exc import IntegrityError

from parent_notifier.core.extensions import db
from parent_notifier.models.accounts import Mentor
from parent_notifier.services.accounts import registration
from parent_notifier.services.accounts.credentials import authenticate, normalise_username
from parent_notifier.services.shared.phone import normalise_indian_mobile


def update_details(mentor: Mentor, full_name: str, username: str, whatsapp_number: str) -> None:
    """Save name, username and number, all already validated by the form."""
    e164 = normalise_indian_mobile(whatsapp_number)
    if e164 is None:
        raise ValueError("The WhatsApp number is not a valid Indian mobile number.")
    mentor.full_name = full_name
    mentor.username = normalise_username(username)
    mentor.whatsapp_number = e164
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
