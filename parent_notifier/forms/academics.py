"""Forms for classes, semesters and students. Each binds only the fields it declares."""

from flask import current_app
from flask_wtf import FlaskForm
from wtforms import SelectField, StringField
from wtforms.validators import InputRequired, Length, NumberRange, ValidationError

from parent_notifier.forms.fields import (
    WholeNumberField,
    department_field,
    indian_mobile,
    printable,
    single_spaced,
    strip,
)
from parent_notifier.models.academics import MAX_SEMESTER, MIN_SEMESTER, ClassGroup
from parent_notifier.services.academics.records import classes, semester_numbers, students
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
    department = department_field("Choose the department")
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


class StatusRulesForm(FlaskForm):
    attendance_threshold = WholeNumberField(
        "Minimum attendance (%)",
        invalid_message="Enter the minimum attendance as a whole number, like 75",
        validators=[
            InputRequired("Enter the minimum attendance"),
            NumberRange(min=1, max=100, message="Minimum attendance must be from 1 to 100"),
        ],
    )
    midsem_max = WholeNumberField(
        "Mid-Sem out of",
        invalid_message="Enter the Mid-Sem total as a whole number, like 20",
        validators=[
            InputRequired("Enter what the Mid-Sem is out of"),
            NumberRange(min=1, max=100, message="Mid-Sem total must be from 1 to 100"),
        ],
    )
    midsem_pass_mark = WholeNumberField(
        "Mid-Sem pass mark",
        invalid_message="Enter the pass mark as a whole number, like 7",
        validators=[
            InputRequired("Enter the Mid-Sem pass mark"),
            NumberRange(min=0, max=100, message="Pass mark must be from 0 to 100"),
        ],
    )

    def validate_midsem_pass_mark(self, field) -> None:
        total = self.midsem_max.data
        if field.data is not None and total is not None and field.data > total:
            raise ValidationError(f"Pass mark cannot be more than the Mid-Sem total of {total}")


class DeleteClassForm(FlaskForm):
    confirmation = StringField(
        "Type the class name to confirm",
        validators=[InputRequired("Type the class name to confirm")],
        filters=[single_spaced],
    )

    def __init__(self, *args, class_name: str, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.class_name = class_name

    def validate_confirmation(self, field) -> None:
        if field.data != self.class_name:
            raise ValidationError(f"Type {self.class_name} exactly to delete this class")


class DeleteStudentForm(FlaskForm):
    confirmation = StringField(
        "Type the enrollment number to confirm",
        validators=[InputRequired("Type the enrollment number to confirm")],
        filters=[single_spaced],
    )

    def __init__(self, *args, enrollment_no: str, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.enrollment_no = enrollment_no

    def validate_confirmation(self, field) -> None:
        if (field.data or "").upper() != self.enrollment_no.upper():
            raise ValidationError(f"Type {self.enrollment_no} exactly to delete this student")


STUDENT_STATUSES = [("active", "Active"), ("left", "Left the class"), ("detained", "Detained")]
ENROLLMENT_TAKEN = "Another student in this class has this enrollment number"


def _text(label: str, required: str | None, limit: int):
    checks = [Length(max=limit, message=f"{label} must be {limit} characters or fewer")]
    if required:
        checks.insert(0, InputRequired(required))
    return StringField(label, validators=[*checks, printable(label)], filters=[single_spaced])


# Created before the shared fields so that, in AddStudentForm, it comes first on the page
# and in the error summary: WTForms orders fields by when they were created.
_ENROLLMENT_FIELD = StringField(
    "Enrollment no.",
    validators=[
        InputRequired("Enter the enrollment number"),
        Length(max=30, message="Enrollment no. must be 30 characters or fewer"),
        printable("Enrollment no."),
    ],
    filters=[strip],
)


class EditStudentForm(FlaskForm):
    """Details only: the enrollment number never changes once the student exists."""

    full_name = _text("Student name", "Enter the student's name", 120)
    parent_name = _text("Parent name", None, 120)
    phone = StringField(
        "Parent phone",
        validators=[InputRequired("Enter the parent's mobile number"), indian_mobile],
        filters=[strip],
    )
    status = SelectField("Status", choices=STUDENT_STATUSES)

    def details(self) -> dict:
        return {name: self[name].data for name in ("full_name", "parent_name", "phone", "status")}


class AddStudentForm(EditStudentForm):
    enrollment_no = _ENROLLMENT_FIELD

    def __init__(self, *args, class_group: ClassGroup, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.class_group = class_group

    def validate_enrollment_no(self, field) -> None:
        if students.enrollment_taken(self.class_group, field.data):
            raise ValidationError(ENROLLMENT_TAKEN)
