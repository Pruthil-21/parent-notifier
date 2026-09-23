from datetime import UTC, datetime

from parent_notifier.services.shared import clock


def test_now_is_aware_utc():
    before = datetime.now(UTC)
    moment = clock.now()
    assert moment.tzinfo is UTC
    assert before <= moment <= datetime.now(UTC)


def test_today_uses_the_college_time_zone(monkeypatch):
    late_evening_utc = datetime(2026, 9, 22, 20, 0, tzinfo=UTC)
    monkeypatch.setattr(clock, "now", lambda: late_evening_utc)
    assert clock.today("Asia/Kolkata").isoformat() == "2026-09-23"
    assert clock.today("UTC").isoformat() == "2026-09-22"
