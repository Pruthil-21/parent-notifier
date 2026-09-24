"""Mentor accounts. One of them may be the admin, set only from the command line."""

from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import CheckConstraint, String, false, true
from sqlalchemy.orm import Mapped, mapped_column

from parent_notifier.core.extensions import db, login_manager
from parent_notifier.models.columns import Timestamps, UTCDateTime

THEMES = ("system", "light", "dark")
MESSAGE_LANGUAGES = ("en", "gu")
ROLES = ("mentor", "admin")


def _one_of(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


class Mentor(UserMixin, Timestamps, db.Model):
    """A faculty mentor. Holds only hashes of the password and recovery code."""

    __tablename__ = "mentors"
    __table_args__ = (
        CheckConstraint("username = lower(username)", name="username_lowercase"),
        CheckConstraint(_one_of("theme", THEMES), name="theme"),
        CheckConstraint(_one_of("message_language", MESSAGE_LANGUAGES), name="message_language"),
        CheckConstraint(_one_of("role", ROLES), name="role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(80))
    username: Mapped[str] = mapped_column(String(30), unique=True)
    whatsapp_number: Mapped[str] = mapped_column(String(16))
    password_hash: Mapped[str] = mapped_column(String(255))
    recovery_code_hash: Mapped[str] = mapped_column(String(255))
    theme: Mapped[str] = mapped_column(String(10), default="system", server_default="system")
    message_language: Mapped[str] = mapped_column(String(2), default="en", server_default="en")
    send_gap_seconds: Mapped[int] = mapped_column(default=20, server_default="20")
    burst_size: Mapped[int] = mapped_column(default=15, server_default="15")
    burst_pause_minutes: Mapped[int] = mapped_column(default=5, server_default="5")
    daily_send_limit: Mapped[int] = mapped_column(default=60, server_default="60")
    # Part of the sign-in cookie; raising it signs the mentor out on every other browser.
    session_version: Mapped[int] = mapped_column(default=1, server_default="1")
    department: Mapped[str | None] = mapped_column(String(60))
    role: Mapped[str] = mapped_column(String(10), default="mentor", server_default="mentor")
    # False while an account request waits for the admin; such accounts cannot sign in.
    approved: Mapped[bool] = mapped_column(default=True, server_default=true())
    # Set when the admin chose the password; the mentor must pick their own next.
    must_change_password: Mapped[bool] = mapped_column(default=False, server_default=false())
    last_sign_in_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    def get_id(self) -> str:
        """What Flask-Login keeps in the session and the remember-me cookie."""
        return f"{self.id}:{self.session_version}"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def initials(self) -> str:
        words = self.full_name.split()
        return "".join(word[0] for word in words[:1] + words[1:][-1:]).upper()

    def __repr__(self) -> str:
        return f"<Mentor {self.id} {self.username}>"


@login_manager.user_loader
def load_mentor(login_id: str) -> Mentor | None:
    """Cookies issued before a password change carry an old version and stop working."""
    mentor_id, _, version = login_id.partition(":")
    if not (mentor_id.isdecimal() and version.isdecimal()):
        return None
    mentor = db.session.get(Mentor, int(mentor_id))
    if mentor is None or mentor.session_version != int(version) or not mentor.approved:
        return None
    return mentor
