import re
import pytest
from werkzeug.security import generate_password_hash
from IISATQR import create_app
from IISATQR.models import db, Teacher, Course, Student, AttendanceSession, AttendanceRecord


@pytest.fixture()
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path/'test.db'}",
        "QR_ROTATION_SECONDS": 25,
        "PUBLIC_BASE_URL": "http://localhost",
    })
    with app.app_context():
        admin = Teacher(staff_id="ADMIN-001", name="Admin", email="admin@test.local", department="SE", password_hash=generate_password_hash("password123"), is_admin=True)
        teacher = Teacher(staff_id="T-002", name="Teacher Two", email="teacher@test.local", department="SE", password_hash=generate_password_hash("password123"))
        course = Course(code="SCD-204", name="Software Construction", department="SE", semester="4", section="A", room="Lab 2")
        course.teachers.append(teacher)
        db.session.add_all([admin, teacher, course]); db.session.flush()
        db.session.add_all([Student(course_id=course.id, registration_no="SE-001", name="Ali"), Student(course_id=course.id, registration_no="SE-002", name="Maryam")]); db.session.commit()
    yield app


@pytest.fixture()
def client(app): return app.test_client()


def login(client, identity="teacher@test.local", password="password123"):
    return client.post("/login", data={"identity": identity, "password": password}, follow_redirects=True)


def test_teacher_login_and_start_creates_absent_records(app, client):
    assert login(client).status_code == 200
    with app.app_context(): cid = Course.query.filter_by(code="SCD-204").first().id
    r = client.post("/sessions/start", data={"course_id": cid, "topic": "Patterns"}, follow_redirects=True)
    assert r.status_code == 200
    with app.app_context():
        s = AttendanceSession.query.first()
        assert len(s.records) == 2
        assert all(x.status == "ABSENT" for x in s.records)


def test_qr_scan_marks_only_matching_student_present(app, client):
    login(client)
    with app.app_context(): cid = Course.query.first().id
    client.post("/sessions/start", data={"course_id": cid})
    with app.app_context(): sid = AttendanceSession.query.first().id
    data = client.get(f"/api/sessions/{sid}/qr").get_json()
    path = re.sub(r"^https?://[^/]+", "", data["url"])
    result = client.post(path, data={"registration_no": "SE-001"})
    assert result.status_code == 200
    with app.app_context():
        records = AttendanceRecord.query.join(Student).order_by(Student.registration_no).all()
        assert records[0].status == "PRESENT"
        assert records[1].status == "ABSENT"


def test_duplicate_scan_does_not_create_duplicate_record(app, client):
    login(client)
    with app.app_context(): cid = Course.query.first().id
    client.post("/sessions/start", data={"course_id": cid})
    with app.app_context(): sid = AttendanceSession.query.first().id
    path = re.sub(r"^https?://[^/]+", "", client.get(f"/api/sessions/{sid}/qr").get_json()["url"])
    client.post(path, data={"registration_no": "SE-001"}); client.post(path, data={"registration_no": "SE-001"})
    with app.app_context(): assert AttendanceRecord.query.count() == 2


def test_admin_teacher_crud_and_course_assignment(app, client):
    login(client, "admin@test.local")
    r = client.post("/teachers/create", data={"staff_id":"T-003","name":"Third","email":"third@test.local","department":"SE","password":"password123"}, follow_redirects=True)
    assert b"Third" in r.data
    with app.app_context():
        t = Teacher.query.filter_by(staff_id="T-003").first(); c = Course.query.first(); tid=t.id; cid=c.id
    client.post(f"/courses/{cid}/edit", data={"code":"SCD-204","name":"Software Construction","department":"SE","semester":"4","section":"A","room":"Lab 3","teacher_ids":[str(tid)]}, follow_redirects=True)
    with app.app_context(): assert db.session.get(Teacher, tid) in db.session.get(Course, cid).teachers


def test_exports(app, client):
    login(client)
    with app.app_context(): cid = Course.query.first().id
    client.post("/sessions/start", data={"course_id":cid})
    with app.app_context(): sid=AttendanceSession.query.first().id
    assert client.get(f"/sessions/{sid}/export/excel").status_code == 200
    assert client.get(f"/sessions/{sid}/export/pdf").status_code == 200
