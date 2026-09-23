"""Filters and validators shared by the forms of every domain."""

from collections.abc import Callable

from wtforms import IntegerField
from wtforms.validators import ValidationError


def strip(value: str | None) -> str | None:
    """WTForms runs filters on GET too, when there is no value yet."""
    return value.strip() if value else value


def single_spaced(value: str | None) -> str | None:
    return " ".join(value.split()) if value else value


def lowercase(value: str | None) -> str | None:
    return value.lower() if value else value


def printable(label: str) -> Callable:
    """Refuse control characters, which would break messages and sheets downstream."""

    def check(_form, field) -> None:
        if any(not char.isprintable() for char in field.data or ""):
            raise ValidationError(f"{label} can only use letters, spaces and punctuation")

    return check


class WholeNumberField(IntegerField):
    """An IntegerField whose "not a number" error says what to enter instead."""

    def __init__(self, label: str, invalid_message: str, **kwargs) -> None:
        super().__init__(label, **kwargs)
        self.invalid_message = invalid_message

    def process_formdata(self, valuelist) -> None:
        try:
            super().process_formdata(valuelist)
        except ValueError:
            raise ValueError(self.invalid_message) from None
