"""College-wide settings the admin changes, each with the value used until then."""

from parent_notifier.core.extensions import db
from parent_notifier.models.college import Setting


def get(key: str, default: str) -> str:
    setting = db.session.get(Setting, key)
    return setting.value if setting else default


def put(key: str, value: str) -> None:
    setting = db.session.get(Setting, key)
    if setting is None:
        db.session.add(Setting(key=key, value=value))
    else:
        setting.value = value
    db.session.commit()
