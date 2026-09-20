
"""Administrator teacher-account management."""

from flask import flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from . import bp
from .helpers import admin_required, current_teacher
from ..extensions import db
from ..models import AttendanceSession, Course, Teacher


@bp.get("/teachers")
@admin_required
def teachers():
    return render_template("teachers.html", teachers=Teacher.query.order_by(Teacher.name).all())


@bp.post("/teachers/create")
@admin_required
def teacher_create():
    staff_id = request.form.get("staff_id", "").strip().upper()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    if not all([staff_id, email, request.form.get("name", "").strip(), request.form.get("department", "").strip()]) or len(password) < 8:
        flash("Complete all teacher fields; password must be at least 8 characters.", "warning")
        return redirect(url_for("main.teachers"))
    teacher = Teacher(staff_id=staff_id, name=request.form["name"].strip(), email=email,
                      department=request.form["department"].strip(), password_hash=generate_password_hash(password),
                      is_admin=request.form.get("is_admin") == "on", is_active=True)
    db.session.add(teacher)
    try:
        db.session.commit()
        flash("Teacher account created.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Staff ID or email already exists.", "danger")
    return redirect(url_for("main.teachers"))


@bp.route("/teachers/<int:teacher_id>/edit", methods=["GET", "POST"])
@admin_required
def teacher_edit(teacher_id):
    teacher = db.session.get(Teacher, teacher_id)

    if not teacher:
        return "Teacher not found", 404

    if request.method == "POST":
        teacher.staff_id = request.form.get(
            "staff_id",
            teacher.staff_id
        ).strip().upper()

        teacher.name = request.form.get(
            "name",
            teacher.name
        ).strip()

        teacher.email = request.form.get(
            "email",
            teacher.email
        ).strip().lower()

        teacher.department = request.form.get(
            "department",
            teacher.department
        ).strip()

        teacher.is_active = request.form.get("is_active") == "on"
        teacher.is_admin = request.form.get("is_admin") == "on"

        # ---------------------------------
        # COURSE ASSIGNMENT
        # ---------------------------------
        course_ids = [
            int(course_id)
            for course_id in request.form.getlist("course_ids")
            if course_id.isdigit()
        ]

        if course_ids:
            assigned_courses = Course.query.filter(
                Course.id.in_(course_ids)
            ).all()

            teacher.courses = assigned_courses
        else:
            teacher.courses = []

        # ---------------------------------
        # PASSWORD CHANGE
        # ---------------------------------
        new_password = request.form.get("new_password", "").strip()

        if new_password:
            if len(new_password) < 8:
                flash(
                    "New password must be at least 8 characters.",
                    "warning"
                )

                return redirect(
                    url_for(
                        "main.teacher_edit",
                        teacher_id=teacher.id
                    )
                )

            teacher.password_hash = generate_password_hash(
                new_password
            )

        try:
            db.session.commit()

            flash(
                "Teacher profile and course assignments updated successfully.",
                "success"
            )

            return redirect(url_for("main.teachers"))

        except IntegrityError:
            db.session.rollback()

            flash(
                "Staff ID or email is already in use.",
                "danger"
            )

    all_courses = Course.query.order_by(
        Course.code,
        Course.semester,
        Course.section
    ).all()

    return render_template(
        "teacher_edit.html",
        item=teacher,
        courses=all_courses
    )


@bp.post("/teachers/<int:teacher_id>/delete")
@admin_required
def teacher_delete(teacher_id):
    teacher = db.session.get(Teacher, teacher_id)
    me = current_teacher()
    if not teacher:
        return "Not found", 404
    if teacher.id == me.id:
        flash("You cannot delete the account currently signed in.", "warning")
    elif AttendanceSession.query.filter_by(created_by=teacher.id).first():
        teacher.is_active = False
        db.session.commit()
        flash("Teacher has attendance history, so the account was disabled instead of deleted.", "warning")
    else:
        db.session.delete(teacher)
        db.session.commit()
        flash("Teacher deleted.", "success")
    return redirect(url_for("main.teachers"))


