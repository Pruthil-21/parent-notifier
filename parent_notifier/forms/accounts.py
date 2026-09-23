"""Forms for signing in, registering, resetting a password and editing the profile."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, HiddenField, PasswordField, StringField
from wtforms.validators import InputRequired


def strip(value: str | None) -> str | None:
    """WTForms runs filters on GET too, when there is no value yet."""
    return value.strip() if value else value


class SignInForm(FlaskForm):
    username = StringField(
        "Username", validators=[InputRequired("Enter your username")], filters=[strip]
    )
    password = PasswordField("Password", validators=[InputRequired("Enter your password")])
    remember = BooleanField("Stay signed in on this computer")
    next = HiddenField()
