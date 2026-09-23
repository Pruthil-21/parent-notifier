"""The one source of the current time, so tests can move the clock without sleeping."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo


def now() -> datetime:
    """Return the current time as an aware UTC datetime."""
    return datetime.now(UTC)


def today(timezone: str) -> date:
    """Today's date where the college is, which is what "this year" means to a mentor."""
    return now().astimezone(ZoneInfo(timezone)).date()
