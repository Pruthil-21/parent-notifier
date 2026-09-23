"""Shared setup for the messaging route tests: a class with two imported students."""

import pytest

from parent_notifier.services.imports.apply import apply_import
from parent_notifier.services.imports.sheet_parser import parse_sheet
from tests.factories.academics import make_class, make_semester
from tests.integration.routes.messaging.send_requests import HEADER, ROWS


@pytest.fixture
def setup(app, mentor):
    with app.app_context():
        class_group = make_class(mentor)
        semester = make_semester(class_group, 4)
        apply_import(class_group, semester, mentor.id, "s", parse_sheet([HEADER, *ROWS], 20), False)
        ids = {s.enrollment_no: s.id for s in semester.students}
        return f"/classes/{class_group.id}/sem/4", ids
