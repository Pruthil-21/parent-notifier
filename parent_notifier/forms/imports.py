"""Forms for uploading a semester sheet and confirming or cancelling its import."""

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import BooleanField, HiddenField

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


class ConfirmImportForm(FlaskForm):
    token = HiddenField()
    update_identity = BooleanField("Update these details from the sheet")
