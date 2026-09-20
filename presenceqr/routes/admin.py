
"""HOD/admin audit-log and system-settings endpoints."""

from flask import flash, redirect, render_template, request, url_for

from . import bp
from .helpers import admin_required, audit
from ..extensions import db
from ..models import AuditLog, SystemSetting


@bp.get("/audit")
@admin_required
def audit_logs():
    q = request.args.get("q", "").strip().lower()
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(500).all()
    if q:
        logs = [x for x in logs if q in x.action.lower() or q in x.entity_type.lower() or q in x.description.lower() or (x.actor and q in x.actor.name.lower())]
    return render_template("audit.html", logs=logs, q=q)


@bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    if request.method == "POST":
        university_name = request.form.get("university_name", "").strip() or "IISAT University, Gujranwala"
        threshold = request.form.get("attendance_threshold", type=float)
        if threshold is None or not 0 <= threshold <= 100:
            flash("Attendance threshold must be between 0 and 100.", "warning")
            return redirect(url_for("main.settings"))
        values = {
            "university_name": university_name,
            "attendance_threshold": str(threshold),
        }
        for key, value in values.items():
            item = SystemSetting.query.filter_by(key=key).first()
            if not item:
                item = SystemSetting(key=key, value=value)
                db.session.add(item)
            else:
                item.value = value
        audit("UPDATE", "SystemSetting", None, "Updated system settings")
        db.session.commit()
        flash("Settings updated.", "success")
        return redirect(url_for("main.settings"))
    return render_template("settings.html")
