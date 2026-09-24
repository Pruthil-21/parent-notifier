"""How dates and numbers read in the interface and in messages: "23 Sep 2026"."""

from datetime import datetime
from zoneinfo import ZoneInfo


def format_date(moment: datetime | None, timezone: str) -> str:
    """A stored UTC time as the local date, like "23 Sep 2026"; empty when missing."""
    if moment is None:
        return ""
    local = moment.astimezone(ZoneInfo(timezone))
    return f"{local.day} {local:%b %Y}"


def format_day_month(moment: datetime, timezone: str) -> str:
    """ "24 Sep", for recent events such as when a parent was messaged."""
    local = moment.astimezone(ZoneInfo(timezone))
    return f"{local.day} {local:%b}"


def format_date_time(moment: datetime, timezone: str) -> str:
    """ "24 Sep 2026, 10:32 PM", for when something happened."""
    local = moment.astimezone(ZoneInfo(timezone))
    return f"{local.day} {local:%b %Y}, {local:%I:%M %p}".replace(", 0", ", ", 1)
