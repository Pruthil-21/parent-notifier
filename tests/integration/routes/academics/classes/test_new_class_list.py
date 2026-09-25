import io
import re

from sqlalchemy import func, select

from parent_notifier.core.extensions import db
from parent_notifier.models.academics import ClassGroup, Semester, Student
from tests.factories.workbooks import make_xlsx, sheet_rows

DETAILS = {"name": "CE-A", "department": "Computer Engineering", "admission_year": "2025"}
LIST_HEADER = ["Enrollment No", "Student Name", "Parent Name", "Parent Phone", "Son / Daughter"]
CLASS_LIST = [
    LIST_HEADER,
    ["12502040500001", "Riya Patel", "Kiran Patel", "90000 00103", "Daughter"],
    ["12502040500002", "Om Desai", "Nilesh Desai", "12345", "Son"],
]


def _create(client, grid, **fields):
    files = {"sheet": (io.BytesIO(make_xlsx(grid)), "class-list.xlsx")}
    data = DETAILS | {"semester": "3"} | fields | files
    return client.post("/classes/new", data=data, content_type="multipart/form-data")


def _token(html):
    return re.search(r'name="token" value="([0-9a-f]{32})"', html).group(1)


def _count(app, model):
    with app.app_context():
        return db.session.scalar(select(func.count()).select_from(model))


def test_a_class_list_is_reviewed_then_saved_to_the_class(app, signed_in_client):
    html = _create(signed_in_client, CLASS_LIST).get_data(as_text=True)
    assert "Review CE-A class list" in html and "Cancelling removes the new class CE-A" in html
    assert "Riya Patel" in html and "Daughter" in html and "not a 10-digit mobile" in html
    assert _count(app, Student) == 0  # nothing added before confirming
    with app.app_context():
        class_group = db.session.scalar(select(ClassGroup))
        [semester] = db.session.scalars(select(Semester)).all()
        base = f"/classes/{class_group.id}/sem/{semester.number}"
    assert semester.number == 3
    signed_in_client.post(f"{base}/import/confirm", data={"token": _token(html)})
    with app.app_context():
        students = db.session.scalars(select(Student).order_by(Student.enrollment_no)).all()
        assert [(s.full_name, s.gender, s.phone_e164) for s in students] == [
            ("Riya Patel", "female", "+919000000103"),
            ("Om Desai", "male", None),
        ]
        assert db.session.get(Semester, semester.id).students == []  # joined by a sheet later
    page = signed_in_client.get(base).get_data(as_text=True)
    assert "2 students are on the class list." in page


def test_the_class_list_format_asks_only_for_contacts(signed_in_client):
    from openpyxl import load_workbook

    response = signed_in_client.get("/class-list-format.xlsx")
    sheet = load_workbook(io.BytesIO(response.data)).active
    assert [cell.value for cell in sheet[1]] == [
        "Enrollment No",
        "Student Name",
        "Parent Name",
        "Parent Phone",
    ]
    no_gender = [LIST_HEADER[:4], [*CLASS_LIST[1][:4]]]
    html = _create(signed_in_client, no_gender).get_data(as_text=True)
    assert "Review CE-A class list" in html and "Son or daughter" not in html


def test_cancelling_the_first_review_removes_the_new_class(app, signed_in_client):
    html = _create(signed_in_client, CLASS_LIST).get_data(as_text=True)
    with app.app_context():
        class_id = db.session.scalar(select(ClassGroup.id))
    response = signed_in_client.post(
        f"/classes/{class_id}/sem/3/import/cancel", data={"token": _token(html)}
    )
    assert response.headers["Location"] == "/classes/"
    assert _count(app, ClassGroup) == 0 and _count(app, Semester) == 0


def test_a_file_with_problems_creates_nothing(app, signed_in_client):
    shortened = [LIST_HEADER, ["1.25020405011E+13", "Riya Patel", "", "90000 00103", ""]]
    html = _create(signed_in_client, shortened).get_data(as_text=True)
    assert "The file has problems" in html and "was shortened by Excel" in html
    assert _count(app, ClassGroup) == 0
    missing = signed_in_client.post("/classes/new", data=DETAILS).get_data(as_text=True)
    assert "Choose the class list, or a semester sheet, to upload" in missing


def test_a_complete_sheet_goes_into_the_current_semester(app, signed_in_client):
    html = _create(signed_in_client, sheet_rows(), semester="").get_data(as_text=True)
    assert "Review Sem" in html and "Subjects" in html
    with app.app_context():
        class_group = db.session.scalar(select(ClassGroup))
        semester = db.session.scalar(select(Semester))
    signed_in_client.post(
        f"/classes/{class_group.id}/sem/{semester.number}/import/confirm",
        data={"token": _token(html)},
    )
    with app.app_context():
        assert len(db.session.get(Semester, semester.id).students) == len(sheet_rows()) - 1
