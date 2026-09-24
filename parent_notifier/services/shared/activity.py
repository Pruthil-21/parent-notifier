"""Adding entries to the activity log, and the plain-English name of each event."""

from datetime import datetime, timedelta

from sqlalchemy import select

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup, Semester, Student
from parent_notifier.models.accounts import Mentor
from parent_notifier.models.activity import ActivityEntry
from parent_notifier.services.shared import clock

# Every event the app logs, by category, with how the logs page names it.
EVENTS = {
    "security": {
        "sign_in": "Signed in",
        "sign_in_failed": "Sign-in failed",
        "sign_in_locked": "Sign-in locked after failed attempts",
        "sign_out": "Signed out",
        "account_created": "Created own account",
        "account_requested": "Requested an account",
        "password_changed": "Changed password",
        "password_chosen": "Chose own password",
        "password_reset": "Reset password with recovery code",
        "recovery_code_regenerated": "Made a new recovery code",
    },
    "admin": {
        "account_created": "Created an account",
        "account_edited": "Edited an account",
        "account_approved": "Approved an account request",
        "request_rejected": "Rejected an account request",
        "password_reset": "Reset a password",
        "signed_out_everywhere": "Signed an account out everywhere",
        "account_deleted": "Deleted an account",
        "classes_transferred": "Transferred classes",
        "signup_mode_changed": "Changed who can create an account",
        "department_added": "Added a department",
        "department_renamed": "Renamed a department",
        "department_removed": "Removed a department",
        "announcement_published": "Published an announcement",
        "announcement_removed": "Removed an announcement",
    },
    "data": {
        "class_created": "Created a class",
        "class_edited": "Edited class details",
        "class_rules_changed": "Changed status rules",
        "class_deleted": "Deleted a class",
        "semester_added": "Added a semester",
        "semester_removed": "Removed a semester",
        "sheet_imported": "Imported a sheet",
        "import_undone": "Undid an import",
        "student_added": "Added a student",
        "student_edited": "Edited a student",
        "student_deleted": "Deleted a student",
    },
    "messaging": {
        "message_sent": "Sent a message",
        "message_skipped": "Skipped a parent",
    },
}
CATEGORY_LABELS = {
    "security": "Sign-in and security",
    "admin": "Admin actions",
    "data": "Data changes",
    "messaging": "Messages",
}


def event_label(category: str, event: str) -> str:
    return EVENTS.get(category, {}).get(event, event.replace("_", " ").capitalize())


def _target(thing) -> tuple[str | None, int | None, str | None]:
    if isinstance(thing, Student):
        return "student", thing.id, f"{thing.full_name} ({thing.enrollment_no})"
    if isinstance(thing, Mentor):
        return "account", thing.id, f"{thing.full_name} ({thing.username})"
    if isinstance(thing, ClassGroup):
        return "class", thing.id, thing.name
    if isinstance(thing, Semester):
        return "semester", thing.id, f"Sem {thing.number}"
    if isinstance(thing, tuple):
        return thing
    return None, None, None


def record(
    category: str,
    event: str,
    *,
    actor: Mentor | None = None,
    username: str | None = None,
    succeeded: bool = True,
    target=None,
    class_group: ClassGroup | None = None,
    ip_address: str | None = None,
    details: dict | None = None,
) -> None:
    """Add one entry. The actor's details are copied, so the entry reads right later.
    `target` is a student, account, class or semester, or a (type, id, label) tuple."""
    if event not in EVENTS.get(category, {}):
        raise ValueError(f"Unknown activity {category}.{event}")
    target_type, target_id, target_label = _target(target)
    db.session.add(
        ActivityEntry(
            category=category,
            event=event,
            succeeded=succeeded,
            actor_id=actor.id if actor else None,
            actor_name=actor.full_name if actor else None,
            username=(actor.username if actor else username or "")[:30] or None,
            department=actor.department if actor else None,
            target_type=target_type,
            target_id=target_id,
            target_label=(target_label or "")[:120] or None,
            class_id=class_group.id if class_group else None,
            class_label=class_group.name if class_group else None,
            ip_address=ip_address,
            details=details,
        )
    )
    db.session.commit()


# Wrong passwords for one username, wherever they were typed.
FAILED_PASSWORD_EVENTS = ("sign_in_failed", "password_reset", "password_changed")


def locked_until(username: str, failures: int, window: timedelta) -> datetime | None:
    """When a username that failed `failures` times within `window` may try again, or
    None. Read from the log, so every server sees the same count."""
    recent = list(
        db.session.scalars(
            select(ActivityEntry.created_at)
            .where(
                ActivityEntry.category == "security",
                ActivityEntry.event.in_(FAILED_PASSWORD_EVENTS),
                ActivityEntry.succeeded.is_(False),
                ActivityEntry.username == username,
                ActivityEntry.created_at >= clock.now() - window,
            )
            .order_by(ActivityEntry.created_at.desc())
            .limit(failures)
        )
    )
    if len(recent) < failures:
        return None
    return recent[-1] + window
