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
