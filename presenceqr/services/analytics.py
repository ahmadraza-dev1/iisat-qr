"""Attendance analytics calculations shared by dashboards and reports."""

from sqlalchemy import extract

from ..models import AttendanceRecord, AttendanceSession


def build_course_analytics(course, month=None, year=None):
    """
    Build attendance analytics for one course.

    If month/year are provided, only sessions from that period are included.
    Percentages are calculated from the attendance records that exist for
    each student in the selected period.
    """
    session_query = AttendanceSession.query.filter(
        AttendanceSession.course_id == course.id
    )

    if month:
        session_query = session_query.filter(
            extract("month", AttendanceSession.started_at) == month
        )

    if year:
        session_query = session_query.filter(
            extract("year", AttendanceSession.started_at) == year
        )

    sessions = session_query.order_by(
        AttendanceSession.started_at.asc()
    ).all()

    session_ids = [item.id for item in sessions]

    if session_ids:
        records = AttendanceRecord.query.filter(
            AttendanceRecord.session_id.in_(session_ids)
        ).all()
    else:
        records = []

    records_by_student = {}

    for record in records:
        records_by_student.setdefault(
            record.student_id,
            []
        ).append(record)

    student_stats = []
    overall_present = 0
    overall_absent = 0

    for student in sorted(
        course.students,
        key=lambda item: item.registration_no
    ):
        student_records = records_by_student.get(
            student.id,
            []
        )

        present = sum(
            1
            for record in student_records
            if record.status == "PRESENT"
        )

        absent = sum(
            1
            for record in student_records
            if record.status == "ABSENT"
        )

        total = present + absent

        percentage = (
            round((present / total) * 100, 1)
            if total
            else 0.0
        )

        overall_present += present
        overall_absent += absent

        student_stats.append({
            "student": student,
            "total": total,
            "present": present,
            "absent": absent,
            "percentage": percentage,
        })

    overall_total = overall_present + overall_absent

    overall_percentage = (
        round(
            (overall_present / overall_total) * 100,
            1
        )
        if overall_total
        else 0.0
    )

    return {
        "sessions": sessions,
        "total_sessions": len(sessions),
        "student_stats": student_stats,
        "overall_present": overall_present,
        "overall_absent": overall_absent,
        "overall_total": overall_total,
        "overall_percentage": overall_percentage,
    }

