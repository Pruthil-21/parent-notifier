"""The one source of the current time, so tests can move the clock without sleeping."""

from datetime import UTC, datetime


def now() -> datetime:
    """Return the current time as an aware UTC datetime."""
    return datetime.now(UTC)
