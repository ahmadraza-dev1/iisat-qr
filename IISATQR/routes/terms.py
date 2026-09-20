
"""Academic-term management."""

from datetime import date

from flask import flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from . import bp
from .helpers import admin_required, audit
from ..extensions import db
from ..models import AcademicTerm


@bp.get("/terms")
@admin_required
def terms():
    items = AcademicTerm.query.order_by(AcademicTerm.is_active.desc(), AcademicTerm.name.desc()).all()
    return render_template("terms.html", terms=items)


@bp.post("/terms/create")
@admin_required
def term_create():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Academic term name is required.", "warning")
        return redirect(url_for("main.terms"))
    start_date = request.form.get("start_date") or None
    end_date = request.form.get("end_date") or None
    try:
        item = AcademicTerm(
            name=name,
            start_date=date.fromisoformat(start_date) if start_date else None,
            end_date=date.fromisoformat(end_date) if end_date else None,
            is_active=True,
        )
        db.session.add(item)
        db.session.flush()
        audit("CREATE", "AcademicTerm", item.id, f"Created academic term {item.name}")
        db.session.commit()
        flash("Academic term created.", "success")
    except (ValueError, IntegrityError):
        db.session.rollback()
        flash("Could not create term. Check dates or duplicate name.", "danger")
    return redirect(url_for("main.terms"))


@bp.post("/terms/<int:term_id>/toggle")
@admin_required
def term_toggle(term_id):
    item = db.session.get(AcademicTerm, term_id)
    if not item:
        return "Not found", 404
    item.is_active = not item.is_active
    audit("UPDATE", "AcademicTerm", item.id, f"Set {item.name} active={item.is_active}")
    db.session.commit()
    flash("Academic term status updated.", "success")
    return redirect(url_for("main.terms"))


