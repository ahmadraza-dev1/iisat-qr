
"""Teacher and HOD dashboard routes."""

from flask import render_template, request

from . import bp
from .helpers import accessible_courses, current_teacher, get_setting, teacher_required
from ..models import AcademicTerm, AttendanceSession, Course, Student, Teacher
from ..services.analytics import build_course_analytics


@bp.get("/dashboard")
@teacher_required
def dashboard():
    teacher = current_teacher()
    term_id = request.args.get("term_id", type=int)
    q = request.args.get("q", "").strip().lower()

    all_courses = accessible_courses(teacher)
    terms = AcademicTerm.query.order_by(AcademicTerm.is_active.desc(), AcademicTerm.name.desc()).all()

    courses = all_courses
    if term_id:
        courses = [c for c in courses if c.academic_term_id == term_id]
    if q:
        courses = [c for c in courses if q in c.code.lower() or q in c.name.lower() or q in c.semester.lower() or q in c.section.lower()]

    course_ids = [c.id for c in all_courses]
    recent = []
    if course_ids:
        recent = AttendanceSession.query.filter(AttendanceSession.course_id.in_(course_ids)).order_by(AttendanceSession.started_at.desc()).limit(12).all()

    active_count = sum(1 for s in recent if s.active)
    total_present = sum(sum(1 for r in s.records if r.status == "PRESENT") for s in recent)
    threshold = float(get_setting("attendance_threshold", "75"))

    low_attendance = 0
    for course in all_courses:
        analytics = build_course_analytics(course)
        low_attendance += sum(1 for row in analytics["student_stats"] if row["total"] and row["percentage"] < threshold)

    admin_stats = None
    if teacher.is_admin:
        admin_stats = {
            "teachers": Teacher.query.filter_by(is_active=True).count(),
            "courses": Course.query.filter_by(is_archived=False).count(),
            "students": Student.query.count(),
            "sessions": AttendanceSession.query.count(),
        }

    return render_template(
        "dashboard.html", teacher=teacher, courses=courses, all_courses=all_courses,
        terms=terms, selected_term_id=term_id, search_query=q, recent=recent,
        active_count=active_count, total_present=total_present,
        low_attendance=low_attendance, threshold=threshold, admin_stats=admin_stats,
    )


