"""Forms for signing in, registering, resetting a password and editing the profile."""

import re

from flask_wtf import FlaskForm
from wtforms import BooleanField, HiddenField, PasswordField, StringField
from wtforms.validators import DataRequired, InputRequired, Length, Regexp, ValidationError

from parent_notifier.forms.fields import indian_mobile, lowercase, printable, single_spaced, strip
from parent_notifier.services.accounts import registration
from parent_notifier.services.accounts.credentials import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH

USERNAME_PATTERN = r"^[a-z0-9][a-z0-9._-]*$"
USERNAME_TAKEN = "That username is taken. Choose another"
_TITLE = re.compile(r"^prof(essor)?\b\.?", re.IGNORECASE)


def _no_title(_form, field) -> None:
    if _TITLE.match(field.data or ""):
        raise ValidationError("Enter your name without Prof., which messages add for you")


def full_name_field() -> StringField:
    return StringField(
        "Full name",
        validators=[
            InputRequired("Enter your full name"),
            Length(max=80, message="Full name must be 80 characters or fewer"),
            printable("Full name"),
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
        validators=[InputRequired("Enter your WhatsApp number"), indian_mobile],
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


class RecoveryCodeSavedForm(FlaskForm):
    saved = BooleanField(
        "I have saved this code",
        validators=[DataRequired("Tick the box to confirm you have saved the code")],
    )


class ResetPasswordForm(FlaskForm):
    username = StringField(
        "Username", validators=[InputRequired("Enter your username")], filters=[strip]
    )
    recovery_code = StringField(
        "Recovery code", validators=[InputRequired("Enter your recovery code")], filters=[strip]
    )
    new_password = new_password_field("New password")


class AccountDetailsForm(FlaskForm):
    full_name = full_name_field()
    username = username_field()
    whatsapp_number = whatsapp_number_field()

    def __init__(self, *args, mentor_id: int, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.mentor_id = mentor_id

    def validate_username(self, field) -> None:
        if registration.username_taken(field.data, except_mentor_id=self.mentor_id):
            raise ValidationError(USERNAME_TAKEN)


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(
        "Current password", validators=[InputRequired("Enter your current password")]
    )
    new_password = new_password_field("New password")


class RegenerateRecoveryCodeForm(FlaskForm):
    # Named `password`, not `current_password`, so its id differs from the password
    # section's field on the same page.
    password = PasswordField(
        "Current password", validators=[InputRequired("Enter your current password")]
    )
