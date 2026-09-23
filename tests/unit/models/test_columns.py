from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import StatementError

from parent_notifier.core.extensions import db
from parent_notifier.services.shared import clock
from tests.factories.accounts import make_mentor

pytestmark = pytest.mark.usefixtures("app_context")

IST = timezone(timedelta(hours=5, minutes=30))


def test_timestamps_come_from_the_clock(monkeypatch):
    fixed = datetime(2026, 9, 23, 4, 30, tzinfo=UTC)
    monkeypatch.setattr(clock, "now", lambda: fixed)
    mentor = make_mentor()
    db.session.expire_all()
    assert mentor.created_at == fixed
    assert mentor.updated_at == fixed
    assert mentor.created_at.tzinfo is UTC


def test_updated_at_moves_on_change(monkeypatch):
    mentor = make_mentor()
    later = datetime(2030, 1, 1, tzinfo=UTC)
    monkeypatch.setattr(clock, "now", lambda: later)
    mentor.full_name = "Asha R. Patel"
    db.session.commit()
    assert mentor.updated_at == later
    assert mentor.created_at < later


def test_other_offsets_are_stored_as_utc():
    mentor = make_mentor()
    mentor.created_at = datetime(2026, 9, 23, 10, 0, tzinfo=IST)
    db.session.commit()
    db.session.expire_all()
    assert mentor.created_at == datetime(2026, 9, 23, 4, 30, tzinfo=UTC)


def test_naive_datetimes_are_refused():
    mentor = make_mentor()
    mentor.created_at = datetime(2026, 9, 23, 10, 0)
    with pytest.raises(StatementError, match="aware datetimes only"):
        db.session.commit()
