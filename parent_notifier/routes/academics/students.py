"""A student's page within a semester, and adding or editing a student."""

from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import login_required

from parent_notifier.forms.academics import ENROLLMENT_TAKEN, AddStudentForm, EditStudentForm
from parent_notifier.routes.academics.semesters import load_semester
from parent_notifier.services.academics import semester_view, students

bp = Blueprint("students", __name__, url_prefix="/classes/<int:class_id>")


@bp.get("/sem/<int:number>/students/<int:student_id>")
@login_required
def detail(class_id: int, number: int, student_id: int):
    class_group, semester = load_semester(class_id, number)
    view = semester_view.build(class_group, semester)
    row = semester_view.find_row(view, student_id)
    if row is None:
        abort(404)
    return render_template(
        "pages/academics/students/detail.html",
        class_group=class_group,
        semester=semester,
        view=view,
        row=row,
    )


def _form_page(class_group, semester, form, student=None):
    return render_template(
        "pages/academics/students/form.html",
        class_group=class_group,
        semester=semester,
        form=form,
        student=student,
    )


@bp.route("/sem/<int:number>/students/new", methods=["GET", "POST"])
@login_required
def add(class_id: int, number: int):
    class_group, semester = load_semester(class_id, number)
    form = AddStudentForm(class_group=class_group)
    if form.validate_on_submit():
        try:
            student = students.add_student(
                class_group, semester, form.enrollment_no.data, form.details()
            )
        except students.EnrollmentTakenError:
            form.enrollment_no.errors.append(ENROLLMENT_TAKEN)
        else:
            flash(f"{student.full_name} added to Sem {number}.", "success")
            return redirect(url_for("semesters.workspace", class_id=class_id, number=number))
    return _form_page(class_group, semester, form)


@bp.route("/sem/<int:number>/students/<int:student_id>/edit", methods=["GET", "POST"])
@login_required
def edit(class_id: int, number: int, student_id: int):
    class_group, semester = load_semester(class_id, number)
    student = students.get_student(class_group, student_id)
    if student is None:
        abort(404)
    # Student has no "phone" attribute, so the keyword fills that field; posted data wins.
    form = EditStudentForm(obj=student, phone=student.phone_raw)
    if form.validate_on_submit():
        students.update_student(student, form.details())
        flash(f"{student.full_name} saved.", "success")
        return redirect(url_for("semesters.workspace", class_id=class_id, number=number))
    return _form_page(class_group, semester, form, student)
