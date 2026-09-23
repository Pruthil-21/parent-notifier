"""Forms for signing in, registering, resetting a password and editing the profile."""

import re

from flask_wtf import FlaskForm
from wtforms import BooleanField, HiddenField, PasswordField, StringField
from wtforms.validators import InputRequired, Length, Regexp, ValidationError

from parent_notifier.services.accounts import registration
from parent_notifier.services.accounts.credentials import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH
from parent_notifier.services.shared.phone import normalise_indian_mobile

USERNAME_PATTERN = r"^[a-z0-9][a-z0-9._-]*$"
USERNAME_TAKEN = "That username is taken. Choose another"
_TITLE = re.compile(r"^prof(essor)?\b\.?", re.IGNORECASE)


def strip(value: str | None) -> str | None:
    """WTForms runs filters on GET too, when there is no value yet."""
    return value.strip() if value else value


def single_spaced(value: str | None) -> str | None:
    return " ".join(value.split()) if value else value


def lowercase(value: str | None) -> str | None:
    return value.lower() if value else value


def _no_title(_form, field) -> None:
    if _TITLE.match(field.data or ""):
        raise ValidationError("Enter your name without Prof., which messages add for you")


def _printable(_form, field) -> None:
    if any(not char.isprintable() for char in field.data or ""):
        raise ValidationError("Full name can only use letters, spaces and punctuation")


def _indian_mobile(_form, field) -> None:
    if normalise_indian_mobile(field.data) is None:
        raise ValidationError("Enter a 10-digit mobile number, like 98765 43210")


def full_name_field() -> StringField:
    return StringField(
        "Full name",
        validators=[
            InputRequired("Enter your full name"),
            Length(max=80, message="Full name must be 80 characters or fewer"),
            _printable,
            _no_title,
        ],
        filters=[single_spaced],
    )


def username_field() -> StringField:
    return StringField(
        "Username",
        validators=[
            InputRequired("Enter a username"),
            Length(min=3, max=30, message="Username must be 3 to 30 characters"),
            Regexp(
                USERNAME_PATTERN,
                message="Username can only use letters, numbers, dots, hyphens and "
                "underscores, and must start with a letter or number",
            ),
        ],
        filters=[strip, lowercase],
    )


def whatsapp_number_field() -> StringField:
    return StringField(
        "WhatsApp number",
        validators=[InputRequired("Enter your WhatsApp number"), _indian_mobile],
        filters=[strip],
    )


def new_password_field(label: str = "Password") -> PasswordField:
    length = f"{MIN_PASSWORD_LENGTH} to {MAX_PASSWORD_LENGTH} characters"
    return PasswordField(
        label,
        validators=[
            InputRequired(f"Enter a {label.lower()}"),
            Length(
                min=MIN_PASSWORD_LENGTH,
                max=MAX_PASSWORD_LENGTH,
                message=f"{label} must be {length}",
            ),
        ],
    )


class SignInForm(FlaskForm):
    username = StringField(
        "Username", validators=[InputRequired("Enter your username")], filters=[strip]
    )
    password = PasswordField("Password", validators=[InputRequired("Enter your password")])
    remember = BooleanField("Stay signed in on this computer")
    next = HiddenField()


class CreateAccountForm(FlaskForm):
    full_name = full_name_field()
    username = username_field()
    whatsapp_number = whatsapp_number_field()
    password = new_password_field()

    def validate_username(self, field) -> None:
        if registration.username_taken(field.data):
            raise ValidationError(USERNAME_TAKEN)
