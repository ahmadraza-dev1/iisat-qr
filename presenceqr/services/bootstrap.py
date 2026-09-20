"""Database compatibility upgrades and first-run seed data."""

import os

from sqlalchemy import inspect, text
from werkzeug.security import generate_password_hash

from ..extensions import db
from ..models import AcademicTerm, SystemSetting, Teacher


def _ensure_legacy_schema(app):
    """Upgrade databases created by older PresenceQR versions without losing data."""
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    if "course" not in tables:
        return

    columns = {col["name"] for col in inspector.get_columns("course")}
    unique_names = {u.get("name") for u in inspector.get_unique_constraints("course")}
    dialect = db.engine.dialect.name
    needs_new_columns = "academic_term_id" not in columns or "is_archived" not in columns
    has_legacy_unique = "uq_course_offering" in unique_names

    if dialect == "sqlite" and (needs_new_columns or has_legacy_unique):
        # SQLite cannot drop a UNIQUE constraint in place. Rebuild only the Course
        # table while foreign keys are temporarily disabled; dependent tables keep
        # their course_id values and point to the newly renamed table afterwards.
        raw = db.engine.raw_connection()
        try:
            cur = raw.cursor()
            cur.execute("PRAGMA foreign_keys=OFF")
            cur.execute("DROP TABLE IF EXISTS course__presenceqr_upgrade")
            cur.execute("""
                CREATE TABLE course__presenceqr_upgrade (
                    id INTEGER NOT NULL PRIMARY KEY,
                    academic_term_id INTEGER,
                    code VARCHAR(40) NOT NULL,
                    name VARCHAR(180) NOT NULL,
                    department VARCHAR(180) NOT NULL,
                    semester VARCHAR(60) NOT NULL,
                    section VARCHAR(30) NOT NULL,
                    room VARCHAR(60) DEFAULT '',
                    is_archived BOOLEAN NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL,
                    FOREIGN KEY(academic_term_id) REFERENCES academic_term (id) ON DELETE SET NULL,
                    CONSTRAINT uq_term_course_offering UNIQUE (academic_term_id, code, section, semester)
                )
            """)
            term_expr = "academic_term_id" if "academic_term_id" in columns else "NULL"
            archived_expr = "COALESCE(is_archived, 0)" if "is_archived" in columns else "0"
            cur.execute(f"""
                INSERT INTO course__presenceqr_upgrade
                (id, academic_term_id, code, name, department, semester, section, room, is_archived, created_at)
                SELECT id, {term_expr}, code, name, department, semester, section, room, {archived_expr}, created_at
                FROM course
            """)
            cur.execute("DROP TABLE course")
            cur.execute("ALTER TABLE course__presenceqr_upgrade RENAME TO course")
            cur.execute("CREATE INDEX IF NOT EXISTS ix_course_code ON course (code)")
            cur.execute("CREATE INDEX IF NOT EXISTS ix_course_name ON course (name)")
            cur.execute("CREATE INDEX IF NOT EXISTS ix_course_department ON course (department)")
            cur.execute("CREATE INDEX IF NOT EXISTS ix_course_semester ON course (semester)")
            cur.execute("CREATE INDEX IF NOT EXISTS ix_course_section ON course (section)")
            cur.execute("CREATE INDEX IF NOT EXISTS ix_course_academic_term_id ON course (academic_term_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS ix_course_is_archived ON course (is_archived)")
            raw.commit()
            cur.execute("PRAGMA foreign_keys=ON")
        finally:
            raw.close()
        return

    statements = []
    if "academic_term_id" not in columns:
        statements.append("ALTER TABLE course ADD COLUMN academic_term_id INTEGER")
    if "is_archived" not in columns:
        statements.append("ALTER TABLE course ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT FALSE")

    with db.engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
        if dialect == "postgresql" and has_legacy_unique:
            conn.execute(text("ALTER TABLE course DROP CONSTRAINT IF EXISTS uq_course_offering"))
            conn.execute(text("ALTER TABLE course ADD CONSTRAINT uq_term_course_offering UNIQUE (academic_term_id, code, section, semester)"))


def _seed_defaults():
    if AcademicTerm.query.count() == 0:
        db.session.add(AcademicTerm(name="Current Term", is_active=True))
        db.session.flush()

    defaults = {
        "university_name": "IISAT University, Gujranwala",
        "attendance_threshold": "75",
        "department_label": "Head of Department",
    }
    for key, value in defaults.items():
        if not SystemSetting.query.filter_by(key=key).first():
            db.session.add(SystemSetting(key=key, value=value))

    default_term = AcademicTerm.query.order_by(AcademicTerm.id).first()
    if default_term:
        from ..models import Course
        Course.query.filter(Course.academic_term_id.is_(None)).update(
            {Course.academic_term_id: default_term.id}, synchronize_session=False
        )
    db.session.commit()
def initialize_database(app):
    """Create tables, run compatibility upgrades, and seed defaults."""
    db.create_all()
    _ensure_legacy_schema(app)
    db.create_all()
    _seed_defaults()

    if not app.config.get("TESTING") and Teacher.query.count() == 0:
        admin = Teacher(
            staff_id=os.getenv("DEFAULT_ADMIN_ID", "ADMIN-001"),
            name=os.getenv("DEFAULT_ADMIN_NAME", "IISAT Administrator"),
            email=os.getenv("DEFAULT_ADMIN_EMAIL", "admin@iisat.edu.pk").lower(),
            department="Administration",
            password_hash=generate_password_hash(
                os.getenv("DEFAULT_ADMIN_PASSWORD", "PresenceQR@123")
            ),
            is_admin=True,
            is_active=True,
        )
        db.session.add(admin)
        db.session.commit()
