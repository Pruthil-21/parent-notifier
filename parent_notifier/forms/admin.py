"""Forms on the admin pages. None of them can set an account's role."""

from flask_wtf import FlaskForm
from wtforms import PasswordField, RadioField, StringField
from wtforms.validators import InputRequired, Length, ValidationError

from parent_notifier.forms.accounts import (
    USERNAME_TAKEN,
    full_name_field,
    username_field,
    whatsapp_number_field,
)
from parent_notifier.forms.fields import department_field, printable, single_spaced
from parent_notifier.services.accounts import registration
from parent_notifier.services.shared import departments


class NewAccountForm(FlaskForm):
    full_name = full_name_field()
    username = username_field()
    whatsapp_number = whatsapp_number_field()
    department = department_field("Choose the department")

    def validate_username(self, field) -> None:
        if registration.username_taken(field.data):
            raise ValidationError(USERNAME_TAKEN)


class ConfirmPasswordForm(FlaskForm):
    password = PasswordField("Your password", validators=[InputRequired("Enter your password")])


SIGNUP_CHOICES = [
    (registration.SIGNUP_OFF, "Only the admin creates accounts"),
    (registration.SIGNUP_APPROVAL, "Anyone can request an account; the admin approves it"),
    (registration.SIGNUP_OPEN, "Anyone can create an account"),
]


class SignupModeForm(FlaskForm):
    mode = RadioField("New accounts", choices=SIGNUP_CHOICES)


class DepartmentForm(FlaskForm):
    """Adding a department, or renaming one (`current` is its present name)."""

    name = StringField(
        "Department name",
        validators=[
            InputRequired("Enter the department's name"),
            Length(max=60, message="Department name must be 60 characters or fewer"),
            printable("Department name"),
        ],
        filters=[single_spaced],
    )

    def __init__(self, *args, current: str | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.current = current

    def validate_name(self, field) -> None:
        listed = departments.canonical(field.data)
        if listed and listed != self.current:
            raise ValidationError(f"{listed} is already listed")
