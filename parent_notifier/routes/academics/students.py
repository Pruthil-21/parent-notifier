"""A student's page within a semester, and adding or editing a student."""

from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import login_required

from parent_notifier.forms.academics import (
    ENROLLMENT_TAKEN,
    AddStudentForm,
    DeleteStudentForm,
    EditStudentForm,
)
from parent_notifier.routes.academics.semesters import load_semester
from parent_notifier.routes.activity import log
from parent_notifier.services.academics.records import students
from parent_notifier.services.academics.views import semester_view

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


def _form_page(class_group, semester, form, student=None, delete_form=None):
    if student is not None and delete_form is None:
        delete_form = DeleteStudentForm(formdata=None, enrollment_no=student.enrollment_no)
    return render_template(
        "pages/academics/students/form.html",
        class_group=class_group,
        semester=semester,
        form=form,
        student=student,
        delete_form=delete_form,
        messages_sent=students.messages_sent(student) if student else 0,
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
            log("data", "student_added", target=student, class_group=class_group)
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
        log(
            "data",
            "student_edited",
            target=student,
            class_group=class_group,
            details={"status": student.status},
        )
        return redirect(url_for("semesters.workspace", class_id=class_id, number=number))
    return _form_page(class_group, semester, form, student)


@bp.post("/sem/<int:number>/students/<int:student_id>/delete")
@login_required
def delete(class_id: int, number: int, student_id: int):
    class_group, semester = load_semester(class_id, number)
    student = students.get_student(class_group, student_id)
    if student is None:
        abort(404)
    form = DeleteStudentForm(enrollment_no=student.enrollment_no)
    if form.validate_on_submit():
        name = student.full_name
        target = ("student", student.id, f"{name} ({student.enrollment_no})")
        students.delete_student(student)
        log("data", "student_deleted", target=target, class_group=class_group)
        flash(f"{name} deleted, with their marks and send record.", "success")
        return redirect(url_for("semesters.workspace", class_id=class_id, number=number))
    edit_form = EditStudentForm(formdata=None, obj=student, phone=student.phone_raw)
    return _form_page(class_group, semester, edit_form, student, delete_form=form)
