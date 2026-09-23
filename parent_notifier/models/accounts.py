"""Mentor accounts."""

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from parent_notifier.core.extensions import db
from parent_notifier.models.columns import Timestamps

THEMES = ("system", "light", "dark")
MESSAGE_LANGUAGES = ("en", "gu")


def _one_of(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


class Mentor(Timestamps, db.Model):
    """A faculty mentor. Holds only hashes of the password and recovery code."""

    __tablename__ = "mentors"
    __table_args__ = (
        CheckConstraint("username = lower(username)", name="username_lowercase"),
        CheckConstraint(_one_of("theme", THEMES), name="theme"),
        CheckConstraint(_one_of("message_language", MESSAGE_LANGUAGES), name="message_language"),
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

    def __repr__(self) -> str:
        return f"<Mentor {self.id} {self.username}>"
