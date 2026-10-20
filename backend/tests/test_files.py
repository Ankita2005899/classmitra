import io
import json
import zipfile
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import files as files_module
from app.main import app

client = TestClient(app)
LESSON = {"title": "Lesson", "sections": [{"heading": "Slide 1", "narration": "Hello class.", "key_points": ["a"]}]}


def signup(role, **extra):
    if role == "admin":
        body = {"name": "File Admin", "employee_id": "F1", "college": "Zeal College", "designation": "Teacher",
                "departments": "AIDS", "email": "files@college.edu", "phone": "", "password": "adminpass1"}
        r = client.post("/api/auth/signup/admin", json=body)
        if r.status_code == 409:
            r = client.post("/api/auth/login", json={"role": "admin", "identifier": "F1", "password": "adminpass1"})
    else:
        body = {"name": "File Student", "college": "Zeal College", "department": "AIDS", "division": "A",
                "roll_number": "77", "email": "filestudent@college.edu", "password": "secret123"}
        r = client.post("/api/auth/signup/student", json=body)
        if r.status_code == 409:
            r = client.post("/api/auth/login", json={"role": "student", "identifier": "77", "password": "secret123"})
    return {"Authorization": "Bearer " + r.json()["token"]}


@pytest.fixture()
def admin(tmp_path, monkeypatch):
    monkeypatch.setattr(files_module, "UPLOAD_DIR", tmp_path)  # test files never go in the real folder
    return signup("admin")


def up(headers, name="notes.xyz", data=b"hello", div="A"):
    return client.post("/api/files/upload", headers=headers, data={"department": "AIDS", "year": "FE", "division": div},
                       files={"file": (name, data, "application/octet-stream")})


def make_pptx(*slides):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for i, text in enumerate(slides, 1):
            zf.writestr(f"ppt/slides/slide{i}.xml",
                        f'<p:sld xmlns:p="p" xmlns:a="a"><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:sld>')
    return buf.getvalue()


def test_any_file_type_can_be_uploaded_listed_downloaded_and_deleted(admin):
    r = up(admin, "weird.name.abc123", b"\x00\x01binary")
    assert r.status_code == 201
    fid = r.json()["id"]
    listing = client.get("/api/files?department=AIDS&year=FE&division=A", headers=admin).json()
    assert [f["id"] for f in listing] == [fid] or fid in [f["id"] for f in listing]
    dl = client.get(f"/api/files/{fid}/download", headers=admin)
    assert dl.content == b"\x00\x01binary" and "attachment" in dl.headers["content-disposition"]
    assert client.delete(f"/api/files/{fid}", headers=admin).status_code == 200
    assert fid not in [f["id"] for f in client.get("/api/files?department=AIDS&year=FE&division=A", headers=admin).json()]


def test_only_admins_can_use_files(admin):
    assert client.get("/api/files?department=AIDS&year=FE&division=A").status_code == 401
    assert client.get("/api/files?department=AIDS&year=FE&division=A", headers=signup("student")).status_code == 401
    assert up(signup("student")).status_code == 401


def test_big_and_empty_files_and_bad_codes_are_refused(admin, monkeypatch):
    assert up(admin, data=b"").status_code == 422
    assert up(admin, div="A/../../x").status_code == 422
    monkeypatch.setattr(files_module, "get_settings", lambda: SimpleNamespace(max_upload_mb=1, gemini_api_key="k", gemini_model="m"))
    assert up(admin, data=b"x" * (1024 * 1024 + 1)).status_code == 413
    assert list(files_module.UPLOAD_DIR.iterdir()) == []  # the half-saved file was removed


def test_explain_reads_every_slide_and_saves_the_lesson(admin, monkeypatch):
    fid = up(admin, "lesson.pptx", make_pptx("Stacks and queues", "Linked lists")).json()["id"]
    seen = {}
    monkeypatch.setattr(files_module, "call_gemini", lambda prompt: seen.setdefault("p", prompt) and json.dumps(LESSON))
    r = client.post(f"/api/files/{fid}/explain", headers=admin)
    assert r.status_code == 200 and r.json()["sections"][0]["heading"] == "Slide 1"
    assert "[Slide 1]" in seen["p"] and "Stacks and queues" in seen["p"] and "Linked lists" in seen["p"]
    assert client.get(f"/api/files/{fid}/explanation", headers=admin).json() == r.json()
    assert [f for f in client.get("/api/files?department=AIDS&year=FE&division=A", headers=admin).json()
            if f["id"] == fid][0]["status"] == "explained"


def test_explain_problems_give_clear_errors(admin, monkeypatch):
    other = up(admin, "movie.mp4", b"abc").json()["id"]
    assert client.post(f"/api/files/{other}/explain", headers=admin).status_code == 422  # cannot read this type
    ok = up(admin, "a.txt", b"Some lesson text").json()["id"]
    monkeypatch.setattr(files_module, "get_settings", lambda: SimpleNamespace(max_upload_mb=25, gemini_api_key="", gemini_model="m"))
    assert client.post(f"/api/files/{ok}/explain", headers=admin).status_code == 503  # no real key
    monkeypatch.setattr(files_module, "call_gemini", lambda p: "this is not json")
    assert client.post(f"/api/files/{ok}/explain", headers=admin).status_code == 502
    bad = up(admin, "broken.pptx", b"not a zip").json()["id"]
    assert client.post(f"/api/files/{bad}/explain", headers=admin).status_code == 422


def test_google_error_reason_is_shown_without_the_key(admin, monkeypatch):
    fid = up(admin, "a.txt", b"Some lesson text").json()["id"]
    monkeypatch.setattr(files_module, "get_settings",
                        lambda: SimpleNamespace(max_upload_mb=25, gemini_api_key="AQ.secret-key-123", gemini_model="m"))

    class Reply:
        status_code = 401

        def json(self):
            return {"error": {"status": "UNAUTHENTICATED", "message": "Expected OAuth 2 access token"}}

    monkeypatch.setattr(files_module.httpx, "post", lambda *a, **k: Reply())
    r = client.post(f"/api/files/{fid}/explain", headers=admin)
    assert r.status_code == 502 and "UNAUTHENTICATED" in r.json()["detail"] and "401" in r.json()["detail"]
    assert "AQ.secret-key-123" not in r.text