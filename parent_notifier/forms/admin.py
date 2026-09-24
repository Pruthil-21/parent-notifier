"""Forms on the admin pages. None of them can set an account's role."""

from flask_wtf import FlaskForm
from wtforms import PasswordField
from wtforms.validators import InputRequired, ValidationError

from parent_notifier.forms.accounts import (
    USERNAME_TAKEN,
    full_name_field,
    username_field,
    whatsapp_number_field,
)
from parent_notifier.forms.fields import department_field
from parent_notifier.services.accounts import registration


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
