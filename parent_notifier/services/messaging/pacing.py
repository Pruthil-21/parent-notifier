"""When the next message may go out, and why not sooner (PROJECT.md 6.6).

Sending many messages quickly from a personal number to people who have not saved it
can get the number restricted. So there is a gap between sends, a pause after each burst
and a daily limit. Only sends count, not skips, and they count across all of a mentor's
classes, because they all come from the same WhatsApp number.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import pairwise
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from parent_notifier.core.extensions import db
from parent_notifier.models.accounts import Mentor
from parent_notifier.models.messaging import SendLog
from parent_notifier.services.shared import clock

GAP, BURST, DAILY = "gap", "burst", "daily"


@dataclass(frozen=True)
class Settings:
    gap_seconds: int
    burst_size: int
    burst_pause_minutes: int
    daily_limit: int


@dataclass(frozen=True)
class Decision:
    wait_seconds: int  # 0 when a send is allowed now
    reason: str | None  # GAP, BURST or DAILY while waiting
    sent_today: int
    daily_limit: int


def decide(
    now: datetime, recent: list[datetime], sent_today: int, settings: Settings, midnight: datetime
) -> Decision:
    """`recent` holds the latest send times, newest first; `midnight` is when the
    mentor's day ends in the college time zone."""

    def wait(until: datetime, reason: str) -> Decision:
        seconds = max(0, int((until - now).total_seconds() + 0.999))
        return Decision(seconds, reason if seconds else None, sent_today, settings.daily_limit)

    if sent_today >= settings.daily_limit:
        return wait(midnight, DAILY)
    pause = timedelta(minutes=settings.burst_pause_minutes)
    burst = recent[: settings.burst_size]
    if len(burst) == settings.burst_size and all(
        newer - older < pause for newer, older in pairwise(burst)
    ):
        decision = wait(burst[0] + pause, BURST)
        if decision.wait_seconds:
            return decision
    if recent:
        return wait(recent[0] + timedelta(seconds=settings.gap_seconds), GAP)
    return Decision(0, None, sent_today, settings.daily_limit)


def settings_for(mentor: Mentor) -> Settings:
    return Settings(
        mentor.send_gap_seconds,
        mentor.burst_size,
        mentor.burst_pause_minutes,
        mentor.daily_send_limit,
    )


def _day_bounds(now: datetime, timezone: str) -> tuple[datetime, datetime]:
    local = now.astimezone(ZoneInfo(timezone))
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def status_for(mentor: Mentor, timezone: str) -> Decision:
    """The mentor's pacing right now, from their send log."""
    now = clock.now()
    settings = settings_for(mentor)
    start, midnight = _day_bounds(now, timezone)
    sent = select(SendLog.created_at).where(
        SendLog.mentor_id == mentor.id, SendLog.status == "sent"
    )
    recent = list(
        db.session.scalars(sent.order_by(SendLog.created_at.desc()).limit(settings.burst_size))
    )
    sent_today = db.session.scalar(
        select(func.count()).select_from(sent.where(SendLog.created_at >= start).subquery())
    )
    return decide(now, recent, sent_today, settings, midnight)
