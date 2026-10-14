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
from .db import Admin, LoginActivity, Student, get_db

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
    """Add 1 to the person's login count and save the time and what they typed."""
    now = datetime.now(timezone.utc)
    row = db.scalar(select(LoginActivity).where(LoginActivity.role == role, LoginActivity.user_id == user.id))
    if row:
        row.login_count += 1
        row.last_login_at = now
        row.identifier = typed
        row.name, row.email = user.name, user.email
    else:
        db.add(LoginActivity(role=role, user_id=user.id, name=user.name, email=user.email,
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