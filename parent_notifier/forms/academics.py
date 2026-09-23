"""Forms for classes, semesters and students. Each binds only the fields it declares."""

from flask import current_app
from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import InputRequired, Length, ValidationError

from parent_notifier.forms.fields import WholeNumberField, printable, single_spaced
from parent_notifier.services.academics import classes
from parent_notifier.services.shared import clock

CLASS_NAME_TAKEN = "You already have a class with this name. Choose another"
FIRST_ADMISSION_YEAR = 2000


def _admission_year_in_range(_form, field) -> None:
    latest = clock.today(current_app.config["APP_TIMEZONE"]).year + 1
    if field.data is not None and not FIRST_ADMISSION_YEAR <= field.data <= latest:
        raise ValidationError(f"Admission year must be between {FIRST_ADMISSION_YEAR} and {latest}")


class ClassDetailsForm(FlaskForm):
    name = StringField(
        "Class name",
        validators=[
            InputRequired("Enter a class name"),
            Length(max=40, message="Class name must be 40 characters or fewer"),
            printable("Class name"),
        ],
        filters=[single_spaced],
    )
    department = StringField(
        "Department",
        validators=[
            InputRequired("Enter the department"),
            Length(max=80, message="Department must be 80 characters or fewer"),
            printable("Department"),
        ],
        filters=[single_spaced],
    )
    admission_year = WholeNumberField(
        "Admission year",
        invalid_message="Enter the admission year as 4 digits, like 2023",
        validators=[InputRequired("Enter the admission year"), _admission_year_in_range],
    )

    def __init__(self, *args, mentor_id: int, class_id: int | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.mentor_id = mentor_id
        self.class_id = class_id

    def validate_name(self, field) -> None:
        if classes.name_taken(self.mentor_id, field.data, except_class_id=self.class_id):
            raise ValidationError(CLASS_NAME_TAKEN)
