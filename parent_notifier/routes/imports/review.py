"""The review page for a staged sheet or class list, and who a staged file belongs to."""

from flask import render_template
from flask_login import current_user

from parent_notifier.models.academics import ClassGroup, Semester
from parent_notifier.services.imports import staging
from parent_notifier.services.imports.compare import compare
from parent_notifier.services.imports.sheet_parser import ParsedSheet

MAX_FILENAME = 120


def owner(class_group: ClassGroup, semester: Semester) -> staging.Owner:
    return staging.Owner(current_user.id, class_group.id, semester.id)


def review(class_group, semester, filename: str, sheet: ParsedSheet, form):
    return render_template(
        "pages/imports/review/page.html",
        class_group=class_group,
        semester=semester,
        filename=filename,
        sheet=sheet,
        comparison=compare(class_group, sheet),
        form=form,
    )
