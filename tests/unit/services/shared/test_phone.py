import pytest

from parent_notifier.services.shared.phone import format_for_display


def test_indian_mobile_is_grouped_for_reading():
    assert format_for_display("+919876543210") == "+91 98765 43210"


@pytest.mark.parametrize("value", ["+14155550100", "+91987654321", "98765 43210", ""])
def test_anything_else_is_shown_unchanged(value):
    assert format_for_display(value) == value
