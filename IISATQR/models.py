"""Database models for IISAT QR.

The schema intentionally preserves the existing table/column names so current
SQLite/PostgreSQL deployments remain compatible with the reorganized codebase.
"""

from datetime import datetime, timezone

from .extensions import db


def utcnow():
    """Return an aware UTC timestamp for model defaults."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Association tables
# ---------------------------------------------------------------------------

course_teachers = db.Table(
    "course_teachers",
    db.Column(
        "course_id",
        db.Integer,
        db.ForeignKey("course.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "teacher_id",
        db.Integer,
        db.ForeignKey("teacher.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


# ---------------------------------------------------------------------------
# Academic structure and users
# ---------------------------------------------------------------------------

class AcademicTerm(db.Model):
    """University term/session such as Fall 2026 or Spring 2027."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False, index=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    courses = db.relationship("Course", back_populates="academic_term", lazy=True)


class Teacher(db.Model):
    """Teacher or administrator account."""

    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.String(40), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    department = db.Column(db.String(180), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    courses = db.relationship(
        "Course",
        secondary=course_teachers,
        back_populates="teachers",
    )


class Course(db.Model):
    """A term-specific course offering."""

    id = db.Column(db.Integer, primary_key=True)
    academic_term_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_term.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    code = db.Column(db.String(40), nullable=False, index=True)
    name = db.Column(db.String(180), nullable=False, index=True)
    department = db.Column(db.String(180), nullable=False, index=True)
    semester = db.Column(db.String(60), nullable=False, index=True)
    section = db.Column(db.String(30), nullable=False, index=True)
    room = db.Column(db.String(60), default="")
    is_archived = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    academic_term = db.relationship("AcademicTerm", back_populates="courses")
    teachers = db.relationship(
        "Teacher",
        secondary=course_teachers,
        back_populates="courses",
    )
    sessions = db.relationship(
        "AttendanceSession",
        backref="course",
        lazy=True,
        cascade="all, delete-orphan",
    )
    students = db.relationship(
        "Student",
        backref="course",
        lazy=True,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "academic_term_id",
            "code",
            "section",
            "semester",
            name="uq_term_course_offering",
        ),
    )


class Student(db.Model):
    """A student enrolled in one course roster."""

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(
        db.Integer,
        db.ForeignKey("course.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    registration_no = db.Column(db.String(80), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    email = db.Column(db.String(180), default="")
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    __table_args__ = (
        db.UniqueConstraint(
            "course_id",
            "registration_no",
            name="uq_course_student_regno",
        ),
    )


# ---------------------------------------------------------------------------
# Attendance domain
# ---------------------------------------------------------------------------

class AttendanceSession(db.Model):
    """One live or completed attendance-taking session."""

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(
        db.Integer,
        db.ForeignKey("course.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by = db.Column(
        db.Integer,
        db.ForeignKey("teacher.id"),
        nullable=False,
        index=True,
    )
    topic = db.Column(db.String(200), default="")
    started_at = db.Column(
        db.DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )
    ended_at = db.Column(db.DateTime(timezone=True), nullable=True)
    active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    creator = db.relationship("Teacher", foreign_keys=[created_by])
    records = db.relationship(
        "AttendanceRecord",
        backref="session",
        lazy=True,
        cascade="all, delete-orphan",
    )


class AttendanceRecord(db.Model):
    """One student's status inside an attendance session."""

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("attendance_session.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("student.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = db.Column(db.String(16), nullable=False, default="ABSENT")
    marked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    ip_address = db.Column(db.String(80), default="")
    user_agent = db.Column(db.String(255), default="")

    student = db.relationship("Student")

    __table_args__ = (
        db.UniqueConstraint(
            "session_id",
            "student_id",
            name="uq_session_student",
        ),
    )


# ---------------------------------------------------------------------------
# Governance and configurable settings
# ---------------------------------------------------------------------------

class AuditLog(db.Model):
    """Append-only operational history for important changes/corrections."""

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(
        db.Integer,
        db.ForeignKey("teacher.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action = db.Column(db.String(80), nullable=False, index=True)
    entity_type = db.Column(db.String(80), nullable=False, index=True)
    entity_id = db.Column(db.Integer, nullable=True, index=True)
    description = db.Column(db.String(500), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=utcnow,
        nullable=False,
        index=True,
    )

    actor = db.relationship("Teacher")


class SystemSetting(db.Model):
    """Small key/value settings controlled by the administrator."""

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.String(500), nullable=False, default="")
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )
