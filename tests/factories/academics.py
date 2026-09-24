from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup, Semester, Student


def make_class(mentor, **fields) -> ClassGroup:
    values = {"name": "CE-A", "department": "Computer Engineering", "admission_year": 2023}
    class_group = ClassGroup(mentor_id=mentor.id, **(values | fields))
    db.session.add(class_group)
    db.session.commit()
    return class_group


def make_semester(class_group, number: int = 1, **fields) -> Semester:
    semester = Semester(class_id=class_group.id, number=number, **fields)
    db.session.add(semester)
    db.session.commit()
    return semester


def make_student(class_group, enrollment_no: str = "23CE001", **fields) -> Student:
    """Fictional details only; phone numbers come from +91 90000 00001 upward."""
    values = {
        "full_name": "Avi Shah",
        "parent_name": "Mehul Shah",
        "phone_raw": "90000 00101",
        "phone_e164": "+919000000101",
    }
    student = Student(class_id=class_group.id, enrollment_no=enrollment_no, **(values | fields))
    db.session.add(student)
    db.session.commit()
    return student


SHEET_HEADER = ["Enrollment No", "Student Name", "Parent Name", "Parent Phone", "DBMS", "OS"]
# One student at risk (23CE001), two needing attention (002, 003) and one doing well.
SHEET_ROWS = [
    ["23CE001", "Avi Shah", "Mehul Shah", "9000000101", "Theory=70,Marks=16", "Theory=80"],
    ["23CE002", "Om Desai", "Nilesh Desai", "9000000102", "Theory=90,Marks=5", "Theory=88"],
    ["23CE003", "Riya Patel", "Kiran Patel", "9000000103", "Theory=90,Marks=15", "Marks=AB"],
    ["23CE004", "Isha Joshi", "Hetal Joshi", "9000000104", "Theory=95,Marks=18", "Theory=91"],
]


def import_sheet(class_group, semester, mentor_id: int, rows=None) -> None:
    """Import a semester sheet the way the confirm step does."""
    from parent_notifier.services.imports.apply import apply_import
    from parent_notifier.services.imports.sheet_parser import parse_sheet

    sheet = parse_sheet([SHEET_HEADER, *(SHEET_ROWS if rows is None else rows)], 20)
    apply_import(class_group, semester, mentor_id, "sheet.xlsx", sheet, update_identity=False)
