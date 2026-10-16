"""Sign up and log in. Students and admins are kept in two separate tables."""
import hashlib
import hmac
import os
import re
import secrets
import time
from datetime import datetime, timezone
from typing import Literal

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import Admin, AdminLogin, Student, StudentLogin, get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])

# If JWT_SECRET is not set, a random one is made on each start (logins end on restart).
SECRET = get_settings().jwt_secret or secrets.token_urlsafe(32)
ROUNDS = 260_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ROUNDS)
    return f"pbkdf2${ROUNDS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, rounds, salt, digest = stored.split("$")
        new = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds))
        return hmac.compare_digest(new.hex(), digest)
    except ValueError:
        return False


_DUMMY = hash_password("dummy-password")  # keeps timing similar when the user is unknown


def make_token(role: str, user_id: int) -> str:
    payload = {"sub": str(user_id), "role": role, "exp": int(time.time()) + 7 * 24 * 3600}
    return jwt.encode(payload, SECRET, algorithm="HS256")


def _email(v: str) -> str:
    v = v.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v):
        raise ValueError("Enter a valid email address")
    return v


class StudentSignup(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=100)
    college: str = Field(min_length=2, max_length=150)
    department: str = Field(min_length=1, max_length=100)
    division: str = Field(min_length=1, max_length=10)
    roll_number: str = Field(min_length=1, max_length=20)
    email: str
    password: str = Field(min_length=8, max_length=128)
    _e = field_validator("email")(_email)


class AdminSignup(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=100)
    employee_id: str = Field(min_length=1, max_length=30)
    college: str = Field(min_length=2, max_length=150)
    designation: str = Field(min_length=1, max_length=50)
    departments: str = Field(min_length=1, max_length=200)
    email: str
    phone: str = Field(default="", max_length=20)
    password: str = Field(min_length=8, max_length=128)
    _e = field_validator("email")(_email)


class LoginIn(BaseModel):
    role: Literal["student", "admin"]
    identifier: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


def _reply(role: str, user) -> dict:
    return {
        "role": role,
        "name": user.name,
        "token": make_token(role, user.id),
        "redirect": "student.html" if role == "student" else "admin.html",
    }


def _record_login(db: Session, role: str, user, typed: str) -> None:
    """Add 1 to the person's login count and save the time and what they typed.

    Students go to the student_logins table, admins to the admin_logins table.
    """
    now = datetime.now(timezone.utc)
    if role == "student":
        model, id_field = StudentLogin, "student_id"
    else:
        model, id_field = AdminLogin, "admin_id"
    row = db.scalar(select(model).where(getattr(model, id_field) == user.id))
    if row:
        row.login_count += 1
        row.last_login_at = now
        row.identifier = typed
        row.name, row.email = user.name, user.email
    else:
        db.add(model(**{id_field: user.id}, name=user.name, email=user.email,
                     identifier=typed, login_count=1, first_login_at=now, last_login_at=now))
    db.commit()


@router.post("/signup/student", status_code=201)
def signup_student(b: StudentSignup, db: Session = Depends(get_db)):
    if db.scalar(select(Student).where(Student.email == b.email)):
        raise HTTPException(409, "This email is already registered as a student.")
    if db.scalar(select(Student).where(
        Student.college == b.college, Student.department == b.department,
        Student.division == b.division, Student.roll_number == b.roll_number,
    )):
        raise HTTPException(409, "This roll number is already registered in this division.")
    s = Student(**b.model_dump(exclude={"password"}), password_hash=hash_password(b.password))
    db.add(s)
    db.commit()
    return _reply("student", s)


@router.post("/signup/admin", status_code=201)
def signup_admin(b: AdminSignup, db: Session = Depends(get_db)):
    if db.scalar(select(Admin).where(Admin.email == b.email)):
        raise HTTPException(409, "This email is already registered as an admin.")
    if db.scalar(select(Admin).where(Admin.college == b.college, Admin.employee_id == b.employee_id)):
        raise HTTPException(409, "This employee ID is already registered for this college.")
    a = Admin(**b.model_dump(exclude={"password"}), password_hash=hash_password(b.password))
    db.add(a)
    db.commit()
    return _reply("admin", a)


@router.post("/login")
def login(b: LoginIn, db: Session = Depends(get_db)):
    """Only the table of the chosen role is checked: a student cannot enter as admin."""
    model = Student if b.role == "student" else Admin
    ident_col = Student.roll_number if b.role == "student" else Admin.employee_id
    ident = b.identifier.strip()
    rows = db.scalars(
        select(model).where(or_(model.email == ident.lower(), ident_col == ident)).limit(20)
    ).all()
    for user in rows:
        if verify_password(b.password, user.password_hash):
            _record_login(db, b.role, user, ident)
            return _reply(b.role, user)
    if not rows:
        verify_password(b.password, _DUMMY)
    raise HTTPException(401, "Wrong details. Check your email, ID or password, and the Student or Admin choice.")


FIREBASE_JWKS = "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"
_jwks_client = jwt.PyJWKClient(FIREBASE_JWKS, cache_keys=True)


def _signing_key(token: str):
    """Google's public key that signed this Firebase token (tests replace this function)."""
    return _jwks_client.get_signing_key_from_jwt(token).key


def verify_firebase_token(token: str) -> dict:
    """Check that a Firebase login token is real, for our project, and not expired."""
    project = get_settings().firebase_project_id
    if not project:
        raise HTTPException(503, "Google and GitHub login is not set up on the server (FIREBASE_PROJECT_ID is empty).")
    try:
        return jwt.decode(
            token, _signing_key(token), algorithms=["RS256"], audience=project,
            issuer=f"https://securetoken.google.com/{project}", leeway=30,
        )
    except jwt.PyJWTError:
        raise HTTPException(401, "Google or GitHub login could not be checked. Please try again.")


class SocialIn(BaseModel):
    role: Literal["student", "admin"]
    id_token: str = Field(min_length=20)


@router.post("/social")
def social_login(b: SocialIn, db: Session = Depends(get_db)):
    """Log in with Google or GitHub (checked by Firebase). The email must already be registered
    in the table of the chosen role, so a student cannot enter as admin this way either."""
    claims = verify_firebase_token(b.id_token)
    email = (claims.get("email") or "").strip().lower()
    if not email or not claims.get("email_verified"):
        raise HTTPException(400, "This account has no verified email. Please log in with your email and password.")
    provider = (claims.get("firebase") or {}).get("sign_in_provider", "social").split(".")[0]  # google / github
    model = Student if b.role == "student" else Admin
    user = db.scalar(select(model).where(model.email == email))
    if not user:
        raise HTTPException(404, {
            "message": f"No {b.role} account found for {email}. Fill in the details below to create one.",
            "name": claims.get("name") or "", "email": email,
        })
    _record_login(db, b.role, user, f"{provider}:{email}")
    return _reply(b.role, user)


@router.get("/me")
def me(authorization: str = Header(default=""), db: Session = Depends(get_db)):
    """Who is logged in? Used by the dashboards to check the token."""
    try:
        data = jwt.decode(authorization.removeprefix("Bearer ").strip(), SECRET, algorithms=["HS256"])
        model = Student if data["role"] == "student" else Admin
        user = db.get(model, int(data["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        user = None
    if not user:
        raise HTTPException(401, "Please log in again.")
    return {"role": data["role"], "name": user.name, "email": user.email, "college": user.college}