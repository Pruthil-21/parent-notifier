"""Forms for classes, semesters and students. Each binds only the fields it declares."""

from flask import current_app
from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import InputRequired, Length, NumberRange, ValidationError

from parent_notifier.forms.fields import WholeNumberField, printable, single_spaced
from parent_notifier.models.academics import MAX_SEMESTER, MIN_SEMESTER, ClassGroup
from parent_notifier.services.academics import classes, semester_numbers
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


class AddSemesterForm(FlaskForm):
    number = WholeNumberField(
        "Semester number",
        invalid_message=f"Enter the semester as a number from {MIN_SEMESTER} to {MAX_SEMESTER}",
        validators=[
            InputRequired("Enter the semester number"),
            NumberRange(
                min=MIN_SEMESTER,
                max=MAX_SEMESTER,
                message=f"Semester must be from {MIN_SEMESTER} to {MAX_SEMESTER}",
            ),
        ],
    )


def add_semester_form(class_group: ClassGroup, formdata=None) -> AddSemesterForm:
    """The add-semester form, pre-filled with the suggested number unless submitted."""
    suggested = semester_numbers.suggest(
        (semester.number for semester in class_group.semesters),
        class_group.admission_year,
        clock.today(current_app.config["APP_TIMEZONE"]),
    )
    return AddSemesterForm(formdata=formdata, data={"number": suggested})
