from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import AdminLogin, SessionLocal, StudentLogin
from app.main import app

client = TestClient(app)

STUDENT = {"name": "Riya Shah", "college": "Zeal College", "department": "AI & Data Science",
           "division": "A", "roll_number": "21", "email": "riya@college.edu", "password": "secret123"}
ADMIN = {"name": "Prof Mehta", "employee_id": "E101", "college": "Zeal College", "designation": "Teacher",
         "departments": "AIDS", "email": "mehta@college.edu", "phone": "9999999999", "password": "adminpass1"}


def login(role, ident, pw):
    return client.post("/api/auth/login", json={"role": role, "identifier": ident, "password": pw})


def test_student_signup_and_login():
    r = client.post("/api/auth/signup/student", json=STUDENT)
    assert r.status_code == 201 and r.json()["redirect"] == "student.html"
    assert login("student", "riya@college.edu", "secret123").status_code == 200
    assert login("student", "21", "secret123").status_code == 200  # roll number works too


def test_student_cannot_enter_as_admin():
    assert login("admin", "riya@college.edu", "secret123").status_code == 401


def test_admin_signup_and_login():
    r = client.post("/api/auth/signup/admin", json=ADMIN)
    assert r.status_code == 201 and r.json()["redirect"] == "admin.html"
    assert login("admin", "E101", "adminpass1").status_code == 200
    assert login("student", "mehta@college.edu", "adminpass1").status_code == 401


def test_duplicate_and_bad_input():
    assert client.post("/api/auth/signup/student", json=STUDENT).status_code == 409
    assert client.post("/api/auth/signup/student", json={**STUDENT, "email": "x@y.zz", "password": "short"}).status_code == 422
    assert login("student", "riya@college.edu", "wrong-password").status_code == 401


def test_me_needs_a_valid_token():
    token = login("student", "riya@college.edu", "secret123").json()["token"]
    ok = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert ok.status_code == 200 and ok.json()["role"] == "student"
    assert client.get("/api/auth/me").status_code == 401


def _row(model, email):
    with SessionLocal() as db:
        return db.scalar(select(model).where(model.email == email))


def test_student_login_is_counted_and_last_login_is_saved():
    s = {**STUDENT, "name": "Aman Patil", "roll_number": "22", "email": "aman@college.edu"}
    assert client.post("/api/auth/signup/student", json=s).status_code == 201
    assert _row(StudentLogin, "aman@college.edu") is None  # signing up is not a login
    assert login("student", "aman@college.edu", "secret123").status_code == 200
    assert login("student", "22", "wrong-password").status_code == 401  # a failed try is not counted
    assert login("student", "22", "secret123").status_code == 200
    r = _row(StudentLogin, "aman@college.edu")
    assert r.login_count == 2
    assert r.identifier == "22"  # what was typed in the login field the last time
    assert r.last_login_at >= r.first_login_at
    assert _row(AdminLogin, "aman@college.edu") is None  # a student never appears in the admin table


def test_admin_login_is_saved_in_the_admin_table():
    assert login("admin", "E101", "adminpass1").status_code == 200
    r = _row(AdminLogin, "mehta@college.edu")
    assert r.login_count >= 1 and r.identifier == "E101"
    assert _row(StudentLogin, "mehta@college.edu") is None