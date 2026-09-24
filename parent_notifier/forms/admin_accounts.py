"""Forms for moving an account's classes and deleting an account."""

from flask_wtf import FlaskForm
from wtforms import SelectField, SelectMultipleField, StringField, widgets
from wtforms.validators import InputRequired, ValidationError

from parent_notifier.forms.fields import single_spaced


class TransferClassesForm(FlaskForm):
    classes = SelectMultipleField(
        "Classes to move",
        coerce=int,
        option_widget=widgets.CheckboxInput(),
        widget=widgets.ListWidget(prefix_label=False),
        validators=[InputRequired("Tick at least one class")],
    )
    to_mentor = SelectField(
        "New mentor", coerce=int, validators=[InputRequired("Choose the new mentor")]
    )

    def __init__(self, *args, classes, mentors, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.classes.choices = [(c.id, c.name) for c in classes]
        self.to_mentor.choices = [(0, "Choose a mentor")] + [
            (m.id, f"{m.full_name} ({m.username})") for m in mentors
        ]

    def validate_to_mentor(self, field) -> None:
        if not field.data:
            raise ValidationError("Choose the new mentor")


class DeleteAccountForm(FlaskForm):
    confirmation = StringField(
        "Type the username to confirm",
        validators=[InputRequired("Type the username to confirm")],
        filters=[single_spaced],
    )

    def __init__(self, *args, username: str, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.username = username

    def validate_confirmation(self, field) -> None:
        if (field.data or "").lower() != self.username:
            raise ValidationError(f"Type {self.username} exactly to delete this account")
