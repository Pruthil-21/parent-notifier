from datetime import UTC, datetime

from parent_notifier.services.shared.formatting import format_date


def test_dates_read_as_day_month_year_in_local_time():
    assert format_date(datetime(2026, 9, 22, 20, 0, tzinfo=UTC), "Asia/Kolkata") == "23 Sep 2026"
    assert format_date(datetime(2026, 3, 5, 6, 0, tzinfo=UTC), "Asia/Kolkata") == "5 Mar 2026"


def test_missing_date_is_empty():
    assert format_date(None, "Asia/Kolkata") == ""
