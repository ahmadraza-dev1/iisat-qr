
"""Course creation, assignment, archive, history, and student detail views."""

from flask import flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from . import bp
from .helpers import (
    accessible_courses,
    admin_required,
    audit,
    can_manage_course,
    current_teacher,
    get_setting,
    teacher_required,
)
from ..extensions import db
from ..models import AcademicTerm, AttendanceRecord, AttendanceSession, Course, Student, Teacher


@bp.get("/courses")
@teacher_required
def courses():
    teacher = current_teacher()
    term_id = request.args.get("term_id", type=int)
    q = request.args.get("q", "").strip().lower()
    show_archived = request.args.get("archived") == "1"

    items = accessible_courses(teacher, include_archived=show_archived)
    if term_id:
        items = [c for c in items if c.academic_term_id == term_id]
    if q:
        items = [c for c in items if q in c.code.lower() or q in c.name.lower() or q in c.semester.lower() or q in c.section.lower()]

    return render_template(
        "courses.html", teacher=teacher, courses=items,
        teachers=Teacher.query.filter_by(is_active=True).order_by(Teacher.name).all() if teacher.is_admin else [],
        terms=AcademicTerm.query.order_by(AcademicTerm.is_active.desc(), AcademicTerm.name.desc()).all(),
        selected_term_id=term_id, search_query=q, show_archived=show_archived,
    )


@bp.post("/courses/create")
@admin_required
def course_create():
    required = ["code", "name", "department", "semester", "section"]
    if any(not request.form.get(k, "").strip() for k in required):
        flash("Complete all required course fields.", "warning")
        return redirect(url_for("main.courses"))

    term_id = request.form.get("academic_term_id", type=int)
    term = db.session.get(AcademicTerm, term_id) if term_id else None
    if not term:
        flash("Select a valid academic term first.", "warning")
        return redirect(url_for("main.courses"))

    item = Course(
        academic_term_id=term.id,
        code=request.form["code"].strip().upper(),
        name=request.form["name"].strip(),
        department=request.form["department"].strip(),
        semester=request.form["semester"].strip(),
        section=request.form["section"].strip().upper(),
        room=request.form.get("room", "").strip(),
        is_archived=False,
    )
    teacher_ids = [int(x) for x in request.form.getlist("teacher_ids") if x.isdigit()]
    item.teachers = Teacher.query.filter(Teacher.id.in_(teacher_ids), Teacher.is_active.is_(True)).all() if teacher_ids else []
    db.session.add(item)
    try:
        db.session.flush()
        audit("CREATE", "Course", item.id, f"Created {item.code} ({term.name})")
        db.session.commit()
        flash("Course created and assigned.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("This course offering already exists in the selected term.", "danger")
    return redirect(url_for("main.courses", term_id=term.id))


@bp.route("/courses/<int:course_id>/edit", methods=["GET", "POST"])
@admin_required
def course_edit(course_id):
    item = db.session.get(Course, course_id)
    if not item:
        return "Not found", 404
    if request.method == "POST":
        item.code = request.form.get("code", item.code).strip().upper()
        item.name = request.form.get("name", item.name).strip()
        item.department = request.form.get("department", item.department).strip()
        item.semester = request.form.get("semester", item.semester).strip()
        item.section = request.form.get("section", item.section).strip().upper()
        item.room = request.form.get("room", item.room).strip()
        term_id = request.form.get("academic_term_id", type=int)
        if term_id and db.session.get(AcademicTerm, term_id):
            item.academic_term_id = term_id
        teacher_ids = [int(x) for x in request.form.getlist("teacher_ids") if x.isdigit()]
        item.teachers = Teacher.query.filter(Teacher.id.in_(teacher_ids), Teacher.is_active.is_(True)).all() if teacher_ids else []
        try:
            audit("UPDATE", "Course", item.id, f"Updated course {item.code}")
            db.session.commit()
            flash("Course updated.", "success")
            return redirect(url_for("main.courses", term_id=item.academic_term_id))
        except IntegrityError:
            db.session.rollback()
            flash("Duplicate course offering.", "danger")
    return render_template(
        "course_edit.html", item=item,
        teachers=Teacher.query.filter_by(is_active=True).order_by(Teacher.name).all(),
        terms=AcademicTerm.query.order_by(AcademicTerm.is_active.desc(), AcademicTerm.name.desc()).all(),
    )


@bp.post("/courses/<int:course_id>/archive")
@admin_required
def course_archive(course_id):
    item = db.session.get(Course, course_id)
    if not item:
        return "Not found", 404
    item.is_archived = not item.is_archived
    audit("ARCHIVE" if item.is_archived else "RESTORE", "Course", item.id, f"{item.code} archived={item.is_archived}")
    db.session.commit()
    flash("Course archived." if item.is_archived else "Course restored.", "success")
    return redirect(url_for("main.courses", archived="1" if item.is_archived else "0"))


@bp.post("/courses/<int:course_id>/delete")
@admin_required
def course_delete(course_id):
    item = db.session.get(Course, course_id)
    if not item:
        return "Not found", 404
    if item.sessions:
        item.is_archived = True
        audit("ARCHIVE", "Course", item.id, f"Archived {item.code} because attendance history exists")
        db.session.commit()
        flash("Course has attendance history, so it was archived instead of permanently deleted.", "warning")
    else:
        audit("DELETE", "Course", item.id, f"Deleted course {item.code}")
        db.session.delete(item)
        db.session.commit()
        flash("Course deleted.", "success")
    return redirect(url_for("main.courses"))




@bp.get("/courses/<int:course_id>/history")
@teacher_required
def course_history(course_id):
    course = db.session.get(Course, course_id)
    if not can_manage_course(current_teacher(), course):
        return "Not found", 404
    sessions = AttendanceSession.query.filter_by(course_id=course.id).order_by(AttendanceSession.started_at.desc()).all()
    return render_template("course_history.html", course=course, sessions=sessions)


@bp.get("/courses/<int:course_id>/students/<int:student_id>")
@teacher_required
def student_detail(course_id, student_id):
    course = db.session.get(Course, course_id)
    student = db.session.get(Student, student_id)
    if not can_manage_course(current_teacher(), course) or not student or student.course_id != course.id:
        return "Not found", 404
    records = AttendanceRecord.query.join(AttendanceSession).filter(
        AttendanceSession.course_id == course.id,
        AttendanceRecord.student_id == student.id,
    ).order_by(AttendanceSession.started_at.desc()).all()
    present = sum(1 for r in records if r.status == "PRESENT")
    absent = sum(1 for r in records if r.status == "ABSENT")
    total = present + absent
    percentage = round((present / total) * 100, 1) if total else 0.0
    return render_template("student_detail.html", course=course, student=student, records=records,
                           present=present, absent=absent, total=total, percentage=percentage,
                           threshold=float(get_setting("attendance_threshold", "75")))


