from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_departments():
    r = client.get("/api/departments")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_get_one_department():
    r = client.get("/api/departments/comp")
    assert r.status_code == 200
    assert r.json()["code"] == "COMP"


def test_unknown_department_is_404():
    assert client.get("/api/departments/nope").status_code == 404


def test_config_check_never_leaks_the_key():
    r = client.get("/api/config-check")
    assert r.status_code == 200
    assert set(r.json().keys()) == {"gemini_key_set"}


def test_health_time_returns_a_valid_time():
    r = client.get("/api/health/time")
    assert r.status_code == 200
    # fromisoformat raises an error if the text is not a valid ISO time
    assert datetime.fromisoformat(r.json()["time"])
