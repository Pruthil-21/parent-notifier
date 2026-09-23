import pytest

from parent_notifier.services.shared.phone import format_for_display, normalise_indian_mobile


def test_indian_mobile_is_grouped_for_reading():
    assert format_for_display("+919876543210") == "+91 98765 43210"


@pytest.mark.parametrize("value", ["+14155550100", "+91987654321", "98765 43210", ""])
def test_anything_else_is_shown_unchanged(value):
    assert format_for_display(value) == value


@pytest.mark.parametrize(
    "raw",
    [
        "9876543210",
        "98765 43210",
        "98765-43210",
        "+91 98765 43210",
        "+91-98765-43210",
        "+91 (98765) 43210",
        "919876543210",
        "09876543210",
        " 98765.43210 ",
    ],
)
def test_common_ways_of_writing_a_mobile_become_e164(raw):
    assert normalise_indian_mobile(raw) == "+919876543210"


@pytest.mark.parametrize(
    "raw",
    ["", "987654321", "98765432101", "5876543210", "+1 415 555 0100", "98765abc10", "+91"],
    ids=["empty", "9 digits", "11 digits", "starts with 5", "not Indian", "letters", "prefix"],
)
def test_anything_that_is_not_an_indian_mobile_is_refused(raw):
    assert normalise_indian_mobile(raw) is None
