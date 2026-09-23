"""What an import would change, for the review page: who is new, and whose name, parent
or phone in the sheet differs from what the class already holds."""

from dataclasses import dataclass, field

from sqlalchemy import select

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup, Student
from parent_notifier.services.imports.sheet_parser import ParsedSheet

FIELDS = (("full_name", "Student name"), ("parent_name", "Parent name"), ("phone", "Phone"))


@dataclass(frozen=True)
class IdentityChange:
    enrollment_no: str
    label: str
    stored: str
    in_sheet: str


@dataclass
class Comparison:
    new_students: int = 0
    existing_students: int = 0
    changes: list[IdentityChange] = field(default_factory=list)


def students_by_enrollment(class_group: ClassGroup) -> dict[str, Student]:
    """Enrollment numbers are matched ignoring case, so 23ce001 finds 23CE001."""
    students = db.session.scalars(select(Student).where(Student.class_id == class_group.id))
    return {student.enrollment_no.upper(): student for student in students}


def compare(class_group: ClassGroup, sheet: ParsedSheet) -> Comparison:
    stored = students_by_enrollment(class_group)
    result = Comparison()
    for row in sheet.rows:
        student = stored.get(row.enrollment_no.upper())
        if student is None:
            result.new_students += 1
            continue
        result.existing_students += 1
        current = {
            "full_name": student.full_name,
            "parent_name": student.parent_name,
            "phone": student.phone_raw,
        }
        incoming = {
            "full_name": row.full_name,
            "parent_name": row.parent_name,
            "phone": row.phone_raw,
        }
        for key, label in FIELDS:
            if _differs(key, current[key], incoming[key], student, row):
                change = IdentityChange(student.enrollment_no, label, current[key], incoming[key])
                result.changes.append(change)
    return result


def _differs(key, stored, incoming, student, row) -> bool:
    """Phones differ only when the numbers do, not the spacing; blanks in the sheet never
    replace stored details."""
    if not incoming:
        return False
    if key == "phone" and row.phone_e164 and row.phone_e164 == student.phone_e164:
        return False
    return " ".join(stored.split()).casefold() != incoming.casefold()
