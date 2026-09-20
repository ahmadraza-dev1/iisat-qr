
"""Course roster management and CSV imports."""

import csv
from io import TextIOWrapper

from flask import flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from . import bp
from .helpers import audit, can_manage_course, current_teacher, teacher_required
from ..extensions import db
from ..models import AttendanceRecord, Course, Student


@bp.route("/courses/<int:course_id>/roster", methods=["GET", "POST"])
@teacher_required
def roster(course_id):
    course = db.session.get(Course, course_id)
    if not can_manage_course(current_teacher(), course):
        return "Not found", 404
    if request.method == "POST":
        bulk = request.form.get("bulk_students", "").strip(); added = updated = skipped = 0
        for raw in bulk.splitlines():
            line = raw.strip()
            if not line: continue
            parts = [p.strip() for p in (line.split(",") if "," in line else line.split("\t"))]
            if len(parts) < 2 or len(parts[0]) < 2 or len(parts[1]) < 2:
                skipped += 1; continue
            reg, name = parts[0].upper(), parts[1]
            email = parts[2].lower() if len(parts) > 2 else ""
            student = Student.query.filter_by(course_id=course.id, registration_no=reg).first()
            if student:
                student.name = name; student.email = email or student.email; updated += 1
            else:
                db.session.add(Student(course_id=course.id, registration_no=reg, name=name, email=email)); added += 1
        db.session.commit(); flash(f"Roster saved: {added} added, {updated} updated, {skipped} skipped.", "success")
        return redirect(url_for("main.roster", course_id=course.id))
    students = Student.query.filter_by(course_id=course.id).order_by(Student.registration_no).all()
    return render_template("roster.html", course=course, students=students)


@bp.post("/courses/<int:course_id>/roster/import-csv")
@teacher_required
def roster_import_csv(course_id):
    course = db.session.get(Course, course_id)
    if not can_manage_course(current_teacher(), course):
        return "Not found", 404
    upload = request.files.get("csv_file")
    if not upload or not upload.filename:
        flash("Choose a CSV file first.", "warning")
        return redirect(url_for("main.roster", course_id=course.id))
    if not upload.filename.lower().endswith(".csv"):
        flash("Only .csv files are supported.", "warning")
        return redirect(url_for("main.roster", course_id=course.id))

    added = updated = skipped = 0
    try:
        wrapper = TextIOWrapper(upload.stream, encoding="utf-8-sig", newline="")
        reader = csv.reader(wrapper)
        for row_no, row in enumerate(reader, start=1):
            if not row or len(row) < 2:
                skipped += 1
                continue
            reg = row[0].strip().upper()
            name = row[1].strip()
            email = row[2].strip().lower() if len(row) > 2 else ""
            if row_no == 1 and reg.lower() in {"registration", "registration no", "registration_no", "reg no"}:
                continue
            if len(reg) < 2 or len(name) < 2:
                skipped += 1
                continue
            student = Student.query.filter_by(course_id=course.id, registration_no=reg).first()
            if student:
                student.name = name
                if email:
                    student.email = email
                updated += 1
            else:
                db.session.add(Student(course_id=course.id, registration_no=reg, name=name, email=email))
                added += 1
        audit("IMPORT", "Student", course.id, f"CSV roster import for {course.code}: {added} added, {updated} updated, {skipped} skipped")
        db.session.commit()
        flash(f"CSV imported: {added} added, {updated} updated, {skipped} skipped.", "success")
    except Exception:
        db.session.rollback()
        flash("CSV import failed. Use UTF-8 CSV with columns: Registration No, Name, Email(optional).", "danger")
    return redirect(url_for("main.roster", course_id=course.id))


@bp.post("/courses/<int:course_id>/students/create")
@teacher_required
def student_create(course_id):
    course = db.session.get(Course, course_id)
    if not can_manage_course(current_teacher(), course): return "Not found", 404
    reg = request.form.get("registration_no", "").strip().upper(); name = request.form.get("name", "").strip()
    if len(reg) < 2 or len(name) < 2:
        flash("Registration number and student name are required.", "warning")
        return redirect(url_for("main.roster", course_id=course.id))
    db.session.add(Student(course_id=course.id, registration_no=reg, name=name, email=request.form.get("email", "").strip().lower()))
    try: db.session.commit(); flash("Student added.", "success")
    except IntegrityError: db.session.rollback(); flash("Registration number already exists in this course.", "danger")
    return redirect(url_for("main.roster", course_id=course.id))


@bp.post("/courses/<int:course_id>/students/<int:student_id>/edit")
@teacher_required
def student_edit(course_id, student_id):
    course = db.session.get(Course, course_id); student = db.session.get(Student, student_id)
    if not can_manage_course(current_teacher(), course) or not student or student.course_id != course.id: return "Not found", 404
    student.registration_no = request.form.get("registration_no", student.registration_no).strip().upper()
    student.name = request.form.get("name", student.name).strip(); student.email = request.form.get("email", student.email).strip().lower()
    try: db.session.commit(); flash("Student updated.", "success")
    except IntegrityError: db.session.rollback(); flash("Registration number already exists.", "danger")
    return redirect(url_for("main.roster", course_id=course.id))



@bp.post("/courses/<int:course_id>/students/<int:student_id>/delete")
@teacher_required
def student_delete(course_id, student_id):
    course = db.session.get(Course, course_id)
    student = db.session.get(Student, student_id)

    if not course:
        return "Course not found", 404

    if not student:
        return "Student not found", 404

    if student.course_id != course.id:
        return "Student does not belong to this course", 404

    if not can_manage_course(current_teacher(), course):
        return "Not authorized", 403

    AttendanceRecord.query.filter_by(
        student_id=student.id
    ).delete(
        synchronize_session=False
    )

    student_name = student.name

    db.session.delete(student)
    db.session.commit()

    flash(
        f"{student_name} deleted successfully.",
        "success"
    )

    return redirect(
        url_for(
            "main.roster",
            course_id=course.id
        )
    )


@bp.post("/courses/<int:course_id>/students/delete-all")
@teacher_required
def students_delete_all(course_id):
    course = db.session.get(Course, course_id)

    if not course:
        return "Course not found", 404

    if not can_manage_course(current_teacher(), course):
        return "Not authorized", 403

    students = Student.query.filter_by(
        course_id=course.id
    ).all()

    if not students:
        flash(
            "No students found.",
            "warning"
        )

        return redirect(
            url_for(
                "main.roster",
                course_id=course.id
            )
        )

    student_ids = [
        student.id
        for student in students
    ]

    AttendanceRecord.query.filter(
        AttendanceRecord.student_id.in_(student_ids)
    ).delete(
        synchronize_session=False
    )

    Student.query.filter_by(
        course_id=course.id
    ).delete(
        synchronize_session=False
    )

    db.session.commit()

    flash(
        f"All {len(students)} students deleted successfully.",
        "success"
    )

    return redirect(
        url_for(
            "main.roster",
            course_id=course.id
        )
    )


