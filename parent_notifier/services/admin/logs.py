"""The activity log page: filters that narrow it down, one page at a time.

Entries older than KEEP_FOR are removed when the page opens; the database refuses to
remove anything under a year old, the minimum the DPDP Rules 2025 ask.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, or_, select

from parent_notifier.core.extensions import db
from parent_notifier.models.activity import CATEGORIES, ActivityEntry
from parent_notifier.services.shared import activity, clock, departments, pagination

PER_PAGE = 50
KEEP_FOR = timedelta(days=400)


def _day(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


@dataclass(frozen=True)
class Filters:
    category: str | None = None
    event: str | None = None
    person: str = ""
    department: str | None = None
    class_name: str = ""
    since: date | None = None
    until: date | None = None
    failed_only: bool = False
    page: int = 1

    @classmethod
    def from_args(cls, args) -> "Filters":
        category = args.get("category")
        category = category if category in CATEGORIES else None
        events = activity.EVENTS.get(category, {}) if category else {}
        event = args.get("event")
        return cls(
            category=category,
            event=event if event in events else None,
            person=" ".join(args.get("person", "").split())[:80],
            department=departments.canonical(args.get("department")),
            class_name=" ".join(args.get("class", "").split())[:40],
            since=_day(args.get("since")),
            until=_day(args.get("until")),
            failed_only=args.get("failed") == "1",
            page=pagination.page_number(args.get("page")),
        )

    @property
    def filtered(self) -> bool:
        return any(
            (
                self.event,
                self.person,
                self.department,
                self.class_name,
                self.since,
                self.until,
                self.failed_only,
            )
        )


def _start_of(day: date, timezone: str) -> datetime:
    return datetime.combine(day, time.min, tzinfo=ZoneInfo(timezone)).astimezone(UTC)


def _contains(column, text: str):
    return func.lower(column).contains(text.lower(), autoescape=True)


def purge_old() -> None:
    db.session.execute(
        delete(ActivityEntry).where(ActivityEntry.created_at < clock.now() - KEEP_FOR)
    )
    db.session.commit()


def entry_page(filters: Filters, timezone: str) -> pagination.Page:
    query = select(ActivityEntry)
    if filters.category:
        query = query.where(ActivityEntry.category == filters.category)
    if filters.event:
        query = query.where(ActivityEntry.event == filters.event)
    if filters.person:
        query = query.where(
            or_(
                _contains(ActivityEntry.actor_name, filters.person),
                _contains(ActivityEntry.username, filters.person),
            )
        )
    if filters.department:
        query = query.where(ActivityEntry.department == filters.department)
    if filters.class_name:
        query = query.where(_contains(ActivityEntry.class_label, filters.class_name))
    if filters.since:
        query = query.where(ActivityEntry.created_at >= _start_of(filters.since, timezone))
    if filters.until:
        next_day = filters.until + timedelta(days=1)
        query = query.where(ActivityEntry.created_at < _start_of(next_day, timezone))
    if filters.failed_only:
        query = query.where(ActivityEntry.succeeded.is_(False))
    return pagination.paginate(query.order_by(ActivityEntry.id.desc()), filters.page, PER_PAGE)


def describe(details: dict | None) -> str:
    """The details of an entry in a few words, like "file sheet.xlsx · added 2"."""
    if not details:
        return ""
    parts = []
    for key, value in details.items():
        shown = ", ".join(value) if isinstance(value, list) else value
        parts.append(f"{key.replace('_', ' ')} {shown}")
    return " · ".join(parts)
