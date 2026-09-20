"""Shared authentication, authorization, settings, and request helpers."""

import socket
from functools import wraps

from flask import current_app, flash, redirect, request, session as login_session, url_for

from ..extensions import db
from ..models import (
    AttendanceRecord,
    AttendanceSession,
    AuditLog,
    Course,
    SystemSetting,
    Teacher,
)


def current_teacher():
    teacher_id = login_session.get("teacher_id")
    return db.session.get(Teacher, teacher_id) if teacher_id else None


def teacher_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        teacher = current_teacher()
        if not teacher or not teacher.is_active:
            login_session.clear()
            return redirect(url_for("main.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    @teacher_required
    def wrapped(*args, **kwargs):
        if not current_teacher().is_admin:
            flash("Administrator access is required.", "danger")
            return redirect(url_for("main.dashboard"))
        return view(*args, **kwargs)

    return wrapped


def can_manage_course(teacher, course):
    return bool(
        teacher
        and course
        and (teacher.is_admin or teacher in course.teachers)
    )


def get_setting(key, default=""):
    try:
        item = SystemSetting.query.filter_by(key=key).first()
        return item.value if item else default
    except Exception:
        return default


def audit(action, entity_type, entity_id, description, actor=None):
    actor = actor or current_teacher()
    db.session.add(
        AuditLog(
            actor_id=actor.id if actor else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description[:500],
        )
    )


def accessible_courses(teacher, include_archived=False):
    if not teacher:
        return []

    if teacher.is_admin:
        query = Course.query
        if not include_archived:
            query = query.filter(Course.is_archived.is_(False))
        return query.order_by(
            Course.academic_term_id.desc(),
            Course.code,
            Course.section,
        ).all()

    items = teacher.courses
    if not include_archived:
        items = [course for course in items if not course.is_archived]

    return sorted(
        items,
        key=lambda course: (
            course.academic_term.name if course.academic_term else "",
            course.code,
            course.section,
        ),
    )


def accessible_session(session_id):
    session = db.session.get(AttendanceSession, session_id)
    if not session or not can_manage_course(current_teacher(), session.course):
        return None
    return session


def finalize_roster_records(session):
    existing_student_ids = {record.student_id for record in session.records}
    for student in session.course.students:
        if student.id not in existing_student_ids:
            db.session.add(
                AttendanceRecord(
                    session_id=session.id,
                    student_id=student.id,
                    status="ABSENT",
                )
            )


def request_base_url():
    configured = current_app.config.get("PUBLIC_BASE_URL")
    if configured:
        return configured

    host = request.host.split(":", 1)[0].lower()
    port = request.host.split(":", 1)[1] if ":" in request.host else ""

    if host in {"127.0.0.1", "localhost"}:
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
            if local_ip and not local_ip.startswith("127."):
                port_suffix = f":{port}" if port else ""
                return f"{request.scheme}://{local_ip}{port_suffix}"
        except OSError:
            pass

    return request.host_url.rstrip("/")
