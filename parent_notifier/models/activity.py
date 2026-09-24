"""The activity log: who did what, and when, for the admin to look back on.

Entries are only ever added. On Postgres a trigger refuses edits, and refuses deletes of
anything less than a year old, the minimum the DPDP Rules 2025 ask logs to be kept.
Names are copied into each entry, so it still reads right after an account changes or
is deleted. Passwords, temporary passwords and recovery codes are never logged.
"""

from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from parent_notifier.core.extensions import db
from parent_notifier.models.columns import UTCDateTime
from parent_notifier.services.shared import clock

CATEGORIES = ("security", "admin", "data", "messaging")


class ActivityEntry(db.Model):
    __tablename__ = "activity_log"
    __table_args__ = (
        Index("ix_activity_log_category_created_at", "category", "created_at"),
        Index("ix_activity_log_actor_id_created_at", "actor_id", "created_at"),
        Index("ix_activity_log_username_created_at", "username", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=lambda: clock.now(), index=True
    )
    category: Mapped[str] = mapped_column(String(12))
    event: Mapped[str] = mapped_column(String(40))
    succeeded: Mapped[bool] = mapped_column(default=True)
    # Who: the account if there is one, and its details as they were at the time. A failed
    # sign-in has no account, only the username that was typed.
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("mentors.id", ondelete="SET NULL"))
    actor_name: Mapped[str | None] = mapped_column(String(80))
    username: Mapped[str | None] = mapped_column(String(30))
    department: Mapped[str | None] = mapped_column(String(60))
    # What it was done to, such as a student, and the class it belongs to.
    target_type: Mapped[str | None] = mapped_column(String(20))
    target_id: Mapped[int | None]
    target_label: Mapped[str | None] = mapped_column(String(120))
    class_id: Mapped[int | None]
    class_label: Mapped[str | None] = mapped_column(String(40))
    # Kept for sign-in and account events only, to spot guessing from one address.
    ip_address: Mapped[str | None] = mapped_column(String(45))
    details: Mapped[dict | None] = mapped_column(JSON)

    def __repr__(self) -> str:
        return f"<ActivityEntry {self.id} {self.category}.{self.event}>"
