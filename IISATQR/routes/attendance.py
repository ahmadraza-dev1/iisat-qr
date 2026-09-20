
"""Live attendance sessions, rotating QR, corrections, and session exports."""

import base64
import time
from datetime import datetime, timezone
from io import BytesIO

import qrcode
from flask import current_app, flash, jsonify, redirect, render_template, request, send_file, url_for

from . import bp
from .helpers import (
    accessible_session,
    audit,
    can_manage_course,
    current_teacher,
    finalize_roster_records,
    request_base_url,
    teacher_required,
)
from ..extensions import db
from ..models import AttendanceRecord, AttendanceSession, Course, Student
from ..reports import build_excel, build_pdf
from ..security import current_slot, make_qr_token, verify_qr_token


@bp.post("/sessions/start")
@teacher_required
def session_start():
    teacher = current_teacher(); course = db.session.get(Course, request.form.get("course_id", type=int))
    if not can_manage_course(teacher, course):
        flash("Invalid or unassigned course.", "danger"); return redirect(url_for("main.dashboard"))
    if not course.students:
        flash("Add the class roster before starting attendance.", "warning"); return redirect(url_for("main.roster", course_id=course.id))
    now = datetime.now(timezone.utc)
    for old in AttendanceSession.query.filter_by(created_by=teacher.id, active=True).all():
        old.active = False; old.ended_at = now; finalize_roster_records(old)
    obj = AttendanceSession(course_id=course.id, created_by=teacher.id, topic=request.form.get("topic", "").strip())
    db.session.add(obj); db.session.flush()
    for student in course.students:
        db.session.add(AttendanceRecord(session_id=obj.id, student_id=student.id, status="ABSENT"))
    db.session.commit()
    return redirect(url_for("main.session_live", session_id=obj.id))


@bp.get("/sessions/<int:session_id>")
@teacher_required
def session_live(session_id):
    obj = accessible_session(session_id)
    if not obj:
        return "Not found", 404
    present = sum(1 for r in obj.records if r.status == "PRESENT")
    return render_template(
        "session_live.html", item=obj, present=present, total=len(obj.records),
        rotation=current_app.config["QR_ROTATION_SECONDS"],
        can_correct=True,
    )


@bp.post("/sessions/<int:session_id>/close")
@teacher_required
def session_close(session_id):
    obj = accessible_session(session_id)
    if not obj: return "Not found", 404
    finalize_roster_records(obj); obj.active = False; obj.ended_at = datetime.now(timezone.utc); db.session.commit()
    flash("Session closed. Present and absent statuses are now final.", "success")
    return redirect(url_for("main.session_live", session_id=obj.id))


@bp.post("/sessions/<int:session_id>/records/<int:record_id>/correct")
@teacher_required
def attendance_correct(session_id, record_id):
    obj = accessible_session(session_id)
    if not obj:
        return "Not found", 404
    record = db.session.get(AttendanceRecord, record_id)
    if not record or record.session_id != obj.id:
        return "Record not found", 404

    new_status = request.form.get("status", "").strip().upper()
    reason = request.form.get("reason", "").strip()
    if new_status not in {"PRESENT", "ABSENT"}:
        flash("Invalid attendance status.", "danger")
        return redirect(url_for("main.session_live", session_id=obj.id))
    if len(reason) < 3:
        flash("Correction reason is required for audit history.", "warning")
        return redirect(url_for("main.session_live", session_id=obj.id))

    old_status = record.status
    record.status = new_status
    record.marked_at = datetime.now(timezone.utc) if new_status == "PRESENT" else None
    audit(
        "ATTENDANCE_CORRECTION", "AttendanceRecord", record.id,
        f"{record.student.registration_no}: {old_status} -> {new_status}. Reason: {reason}"
    )
    db.session.commit()
    flash(f"Attendance corrected for {record.student.name}.", "success")
    return redirect(url_for("main.session_live", session_id=obj.id))


@bp.get("/api/sessions/<int:session_id>/qr")
@teacher_required
def api_qr(session_id):
    obj = accessible_session(session_id)
    if not obj: return jsonify({"error": "not found"}), 404
    if not obj.active: return jsonify({"error": "session closed"}), 409
    token = make_qr_token(obj.id); attend_url = f"{request_base_url()}{url_for('main.attend', token=token)}"
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_Q, box_size=9, border=4)
    qr.add_data(attend_url); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    buff = BytesIO(); img.save(buff, format="PNG")
    rotation = current_app.config["QR_ROTATION_SECONDS"]; remaining = rotation - (int(time.time()) % rotation)
    return jsonify({"image": "data:image/png;base64," + base64.b64encode(buff.getvalue()).decode(), "url": attend_url,
                    "remaining": remaining, "subject": f"{obj.course.code} — {obj.course.name}", "slot": current_slot()})


@bp.get("/api/sessions/<int:session_id>/attendance")
@teacher_required
def api_attendance(session_id):
    obj = accessible_session(session_id)
    if not obj: return jsonify({"error": "not found"}), 404
    rows = sorted(obj.records, key=lambda r: (r.status != "PRESENT", r.student.registration_no))
    return jsonify({"present": sum(1 for r in rows if r.status == "PRESENT"), "total": len(rows),
                    "rows": [{"registration_no": r.student.registration_no, "student_name": r.student.name, "status": r.status,
                              "marked_at": r.marked_at.astimezone().strftime("%I:%M:%S %p") if r.marked_at and r.marked_at.tzinfo else (r.marked_at.strftime("%I:%M:%S %p") if r.marked_at else "—")} for r in rows]})


@bp.route("/attend/<token>", methods=["GET", "POST"])
def attend(token):
    payload = verify_qr_token(token); obj = db.session.get(AttendanceSession, payload["sid"]) if payload else None
    if not obj or not obj.active:
        return render_template("student_attend.html", valid=False, message="This QR expired or the session is closed."), 410
    if request.method == "POST":
        if not verify_qr_token(token):
            return render_template("student_attend.html", valid=False, message="QR expired. Scan the newest QR on screen."), 410
        reg = request.form.get("registration_no", "").strip().upper()
        student = Student.query.filter_by(course_id=obj.course_id, registration_no=reg).first()
        if not student:
            return render_template("student_attend.html", valid=True, item=obj, error="Registration number is not enrolled in this class."), 403
        record = AttendanceRecord.query.filter_by(session_id=obj.id, student_id=student.id).first()
        if not record:
            record = AttendanceRecord(session_id=obj.id, student_id=student.id, status="ABSENT"); db.session.add(record)
        duplicate = record.status == "PRESENT"
        if not duplicate:
            record.status = "PRESENT"; record.marked_at = datetime.now(timezone.utc)
            record.ip_address = request.headers.get("X-Forwarded-For", request.remote_addr or "")[:80]
            record.user_agent = request.headers.get("User-Agent", "")[:255]
            db.session.commit()
        return render_template("student_success.html", duplicate=duplicate, item=obj, student=student)
    return render_template("student_attend.html", valid=True, item=obj)


@bp.get("/sessions/<int:session_id>/export/excel")
@teacher_required
def export_excel(session_id):
    obj = accessible_session(session_id)
    if not obj: return "Not found", 404
    finalize_roster_records(obj); db.session.commit()
    return send_file(build_excel(obj), as_attachment=True, download_name=f"IISAT_QR_{obj.course.code}_{obj.started_at.strftime('%Y-%m-%d')}.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@bp.get("/sessions/<int:session_id>/export/pdf")
@teacher_required
def export_pdf(session_id):
    obj = accessible_session(session_id)
    if not obj: return "Not found", 404
    finalize_roster_records(obj); db.session.commit()
    return send_file(build_pdf(obj), as_attachment=True, download_name=f"IISAT_QR_{obj.course.code}_{obj.started_at.strftime('%Y-%m-%d')}.pdf", mimetype="application/pdf")
