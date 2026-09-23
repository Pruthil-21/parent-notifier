from datetime import UTC, datetime

from parent_notifier.services.shared import clock


def test_now_is_aware_utc():
    before = datetime.now(UTC)
    moment = clock.now()
    assert moment.tzinfo is UTC
    assert before <= moment <= datetime.now(UTC)
