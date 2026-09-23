from parent_notifier.core.extensions import db
from parent_notifier.models.accounts import Mentor
from parent_notifier.services.accounts.credentials import hash_password

PASSWORD = "Winter-lecture-42"


def make_mentor(password: str | None = None, **fields) -> Mentor:
    """A saved mentor. Pass `password` to get a real hash; otherwise the hash is a
    placeholder that never matches, which keeps tests that do not sign in fast."""
    values = {
        "full_name": "Asha Patel",
        "username": "ashapatel",
        "whatsapp_number": "+919000000001",
        "password_hash": hash_password(password) if password else "not-a-real-hash",
        "recovery_code_hash": "not-a-real-hash",
    }
    mentor = Mentor(**(values | fields))
    db.session.add(mentor)
    db.session.commit()
    return mentor


def sign_in(client, username: str = "ashapatel", password: str = PASSWORD, **fields):
    return client.post("/sign-in", data={"username": username, "password": password} | fields)
