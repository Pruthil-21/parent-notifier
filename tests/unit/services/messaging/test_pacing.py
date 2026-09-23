from datetime import UTC, datetime, timedelta

import pytest

from parent_notifier.core.extensions import db
from parent_notifier.services.messaging import pacing, send_log
from parent_notifier.services.messaging.pacing import BURST, DAILY, GAP, Settings, decide
from parent_notifier.services.shared import clock
from tests.factories.academics import make_class, make_semester, make_student
from tests.factories.accounts import make_mentor

NOW = datetime(2026, 9, 24, 6, 0, tzinfo=UTC)
MIDNIGHT = datetime(2026, 9, 24, 18, 30, tzinfo=UTC)  # midnight in India
SETTINGS = Settings(gap_seconds=20, burst_size=3, burst_pause_minutes=5, daily_limit=10)


def ago(*seconds):
    return [NOW - timedelta(seconds=s) for s in seconds]


@pytest.mark.parametrize(
    ("recent", "sent_today", "expected"),
    [
        ([], 0, (0, None)),
        (ago(5), 1, (15, GAP)),
        (ago(25), 1, (0, None)),
        (ago(30, 60, 90), 3, (270, BURST)),
        (ago(30, 60, 400), 3, (0, None)),
        (ago(301, 330, 360), 3, (0, None)),
        (ago(3600), 10, (45000, DAILY)),
    ],
    ids=["first send", "inside gap", "gap over", "burst", "no burst", "pause over", "daily"],
)
def test_decisions(recent, sent_today, expected):
    decision = decide(NOW, recent, sent_today, SETTINGS, MIDNIGHT)
    assert (decision.wait_seconds, decision.reason) == expected
    assert (decision.sent_today, decision.daily_limit) == (sent_today, 10)


@pytest.mark.usefixtures("app_context")
def test_status_counts_only_todays_sends_across_classes(monkeypatch):
    mentor = make_mentor()
    students = []
    for name in ("CE-A", "CE-B"):
        class_group = make_class(mentor, name=name)
        semester = make_semester(class_group, 4)
        students.append((semester, make_student(class_group)))
    times = iter([NOW - timedelta(days=1), NOW - timedelta(minutes=9), NOW - timedelta(seconds=8)])
    monkeypatch.setattr(clock, "now", lambda: next(times))
    for (semester, student), status in zip(students * 2, ["sent", "sent", "skipped"], strict=False):
        send_log.record(semester, student.id, mentor.id, status=status, language="en")
    monkeypatch.setattr(clock, "now", lambda: NOW)
    decision = pacing.status_for(mentor, "Asia/Kolkata")
    assert decision.sent_today == 1
    assert decision.reason is None
    mentor.daily_send_limit = 1
    db.session.commit()
    assert pacing.status_for(mentor, "Asia/Kolkata").reason == DAILY
