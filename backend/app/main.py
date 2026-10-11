from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .data import DEPARTMENTS

settings = get_settings()

app = FastAPI(title="ClassMitra API", version="0.1.0")

# CORS: lets the website (a different address) call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    """Is the server alive? Used by you, by tests, and later by hosting."""
    return {"status": "ok", "env": settings.app_env}


@app.get("/api/health/time")
def health_time():
    """Current server time in UTC (ISO 8601 text). Handy to check the server clock."""
    return {"time": datetime.now(timezone.utc).isoformat()}


@app.get("/api/config-check")
def config_check():
    """Tells you whether a secret is loaded, WITHOUT ever returning its value."""
    return {"gemini_key_set": bool(settings.gemini_api_key)}


@app.get("/api/departments")
def list_departments():
    """GET a collection: returns every department."""
    return DEPARTMENTS


@app.get("/api/departments/{dept_id}")
def get_department(dept_id: str):
    """GET one item by id: returns 404 if it does not exist."""
    for dept in DEPARTMENTS:
        if dept["id"] == dept_id:
            return dept
    raise HTTPException(status_code=404, detail="Department not found")


# ---- Website pages (so the site also opens on Render) ----
# The first page people see (/) is the login page. The dashboard is /index.html.
# Only these pages and the css/js folders are shared. The rest of the repo,
# including backend/.env, is never served.
SITE_DIR = Path(__file__).resolve().parents[2]
PAGES = {"/": "login.html", "/index.html": "index.html", "/login.html": "login.html", "/student.html": "student.html", "/admin.html": "admin.html", "/studio.html": "studio.html"}


def _page(filename: str):
    def serve():
        return FileResponse(SITE_DIR / filename)
    return serve


for _url, _file in PAGES.items():
    if (SITE_DIR / _file).is_file():
        app.add_api_route(_url, _page(_file), methods=["GET"], include_in_schema=False)

for _folder in ("css", "js"):
    if (SITE_DIR / _folder).is_dir():
        app.mount(f"/{_folder}", StaticFiles(directory=SITE_DIR / _folder), name=_folder)