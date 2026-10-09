from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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