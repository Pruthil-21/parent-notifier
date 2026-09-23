"""Filters and validators shared by the forms of every domain."""

from collections.abc import Callable

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
