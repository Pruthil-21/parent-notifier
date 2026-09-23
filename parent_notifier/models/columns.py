"""Column types and mixins shared by every model."""

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from parent_notifier.services.shared import clock


class UTCDateTime(TypeDecorator[datetime]):
    """Stores UTC without an offset and hands back aware UTC datetimes.

    SQLite has no time zone type and returns naive values, which compare wrongly against
    aware ones. Refusing naive input keeps local times from being stored as if they were UTC.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Store aware datetimes only; use clock.now().")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return None if value is None else value.replace(tzinfo=UTC)


class Timestamps:
    """`created_at` and `updated_at`, both read from the injectable clock."""

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=lambda: clock.now())
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=lambda: clock.now(), onupdate=lambda: clock.now()
    )
