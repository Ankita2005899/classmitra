from fastapi.testclient import TestClient

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
