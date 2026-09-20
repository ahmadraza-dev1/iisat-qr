
"""Public landing, sign-in/sign-out, profile, and health endpoints."""

from flask import jsonify, redirect, render_template, request, session as login_session, url_for, flash
from werkzeug.security import check_password_hash, generate_password_hash

from . import bp
from .helpers import current_teacher, teacher_required
from ..extensions import db
from ..models import Teacher


@bp.get("/")
def home():
    return render_template("home.html", teacher=current_teacher())


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_teacher():
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        identity = request.form.get("identity", "").strip().lower()
        password = request.form.get("password", "")
        teacher = Teacher.query.filter((Teacher.email == identity) | (db.func.lower(Teacher.staff_id) == identity)).first()
        if teacher and teacher.is_active and check_password_hash(teacher.password_hash, password):
            login_session.clear()
            login_session["teacher_id"] = teacher.id
            login_session.permanent = True
            return redirect(url_for("main.dashboard"))
        flash("Invalid credentials or disabled account.", "danger")
    return render_template("login.html")


@bp.post("/logout")
def logout():
    login_session.clear()
    return redirect(url_for("main.home"))



@bp.get("/health")
def health():
    return jsonify({"status": "ok", "service": "IISAT QR"})


@bp.route("/profile", methods=["GET", "POST"])
@teacher_required
def profile():
    teacher = current_teacher()
    if request.method == "POST":
        teacher.name = request.form.get("name", teacher.name).strip() or teacher.name
        teacher.department = request.form.get("department", teacher.department).strip() or teacher.department
        password = request.form.get("new_password", "")
        if password:
            if len(password) < 8:
                flash("Password must be at least 8 characters.", "warning"); return redirect(url_for("main.profile"))
            teacher.password_hash = generate_password_hash(password)
        db.session.commit(); flash("Profile updated.", "success"); return redirect(url_for("main.profile"))
    return render_template("profile.html", teacher=teacher)
