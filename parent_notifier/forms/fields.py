"""Filters and validators shared by the forms of every domain."""

from collections.abc import Callable

from wtforms import IntegerField, StringField
from wtforms.validators import InputRequired, ValidationError

from parent_notifier.services.shared import departments
from parent_notifier.services.shared.phone import normalise_indian_mobile


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


def indian_mobile(_form, field) -> None:
    if normalise_indian_mobile(field.data) is None:
        raise ValidationError("Enter a 10-digit mobile number, like 98765 43210")


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


def _listed_department(_form, field) -> None:
    if field.data not in departments.DEPARTMENTS:
        raise ValidationError("Choose a department from the list")


def department_field(required: str = "Choose your department") -> StringField:
    """Typed with suggestions from the college's list; only a listed department is kept,
    written the way the list writes it."""
    return StringField(
        "Department",
        validators=[InputRequired(required), _listed_department],
        filters=[lambda value: departments.canonical(value) or value],
    )
