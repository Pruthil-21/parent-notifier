"""Forms for uploading a semester sheet and confirming or cancelling its import."""

from datetime import date

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import BooleanField, DateField, HiddenField
from wtforms.validators import Optional

ALLOWED_EXTENSIONS = ["xlsx", "csv"]


class UploadSheetForm(FlaskForm):
    sheet = FileField(
        "Semester sheet",
        validators=[
            FileRequired("Choose the semester's sheet to upload"),
            FileAllowed(
                ALLOWED_EXTENSIONS,
                "Upload an Excel (.xlsx) or CSV (.csv) file. Save old .xls files as .xlsx first",
            ),
        ],
    )

    attendance_from = DateField(
        "Attendance from", validators=[Optional()], render_kw={"autocomplete": "off"}
    )
    attendance_to = DateField(
        "Attendance to", validators=[Optional()], render_kw={"autocomplete": "off"}
    )

    def validate(self, extra_validators=None) -> bool:
        """The dates are checked together; an empty date stops its own field's checks."""
        valid = super().validate(extra_validators)
        if self.attendance_from.errors or self.attendance_to.errors:
            return False
        start, end = self.attendance_from.data, self.attendance_to.data
        problem = None
        if (start is None) != (end is None):
            problem = "Enter both attendance dates, or leave both empty"
        elif start and end and not date(2000, 1, 1) <= start <= end <= date(2100, 12, 31):
            problem = "The attendance period must end on or after it starts"
        if problem:
            self.attendance_to.errors.append(problem)
            return False
        return valid

    @classmethod
    def for_semester(cls, semester) -> "UploadSheetForm":
        """A fresh form, starting from the period of the semester's last sheet."""
        return cls(
            formdata=None,
            attendance_from=semester.attendance_from,
            attendance_to=semester.attendance_to,
        )

    def period(self) -> tuple[str | None, str | None]:
        """The period as ISO dates for the staged sheet, or no period."""
        start, end = self.attendance_from.data, self.attendance_to.data
        return (start.isoformat(), end.isoformat()) if start and end else (None, None)


class ConfirmImportForm(FlaskForm):
    token = HiddenField()
    update_identity = BooleanField("Update these details from the sheet")
