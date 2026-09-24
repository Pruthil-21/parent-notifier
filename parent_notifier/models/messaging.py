"""The record of every message sent to, or skipped for, a parent."""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from parent_notifier.core.extensions import db
from parent_notifier.models.columns import UTCDateTime
from parent_notifier.services.shared import clock

SEND_STATUSES = ("sent", "skipped")


class SendLog(db.Model):
    """One send or skip. `round` ties it to the import it was based on, so a new import
    makes everyone pending again, and undoing it brings these marks back."""

    __tablename__ = "send_log"
    __table_args__ = (
        CheckConstraint("status IN ('sent', 'skipped')", name="status"),
        CheckConstraint("language IN ('en', 'gu')", name="language"),
        Index("ix_send_log_semester_round", "semester_id", "round"),
        Index("ix_send_log_mentor_created", "mentor_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    semester_id: Mapped[int] = mapped_column(ForeignKey("semesters.id", ondelete="CASCADE"))
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    # Who sent it. Empty once that account is deleted; the record stays with the class.
    mentor_id: Mapped[int | None] = mapped_column(ForeignKey("mentors.id", ondelete="SET NULL"))
    round: Mapped[int]
    status: Mapped[str] = mapped_column(String(10))
    language: Mapped[str] = mapped_column(String(2))
    note: Mapped[str] = mapped_column(String(500), default="", server_default="")
    # The exact text that was opened in WhatsApp, as a record of what the parent received.
    message: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=lambda: clock.now())
