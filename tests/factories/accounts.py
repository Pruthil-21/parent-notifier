from parent_notifier.core.extensions import db
from parent_notifier.models.accounts import Mentor


def make_mentor(**fields) -> Mentor:
    values = {
        "full_name": "Asha Patel",
        "username": "ashapatel",
        "whatsapp_number": "+919000000001",
        "password_hash": "not-a-real-hash",
        "recovery_code_hash": "not-a-real-hash",
    }
    mentor = Mentor(**(values | fields))
    db.session.add(mentor)
    db.session.commit()
    return mentor
