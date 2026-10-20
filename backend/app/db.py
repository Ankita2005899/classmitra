"""Database connection and the two tables: students and admins.

MySQL (Workbench) for real work, or a local SQLite file if DATABASE_URL is empty.
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .config import get_settings

_url = get_settings().database_url
if _url.startswith("sqlite"):
    _args = {"check_same_thread": False}
elif any(h in _url for h in ("@localhost", "@127.0.0.1")):
    _args = {}
else:  # cloud MySQL (Aiven, TiDB...) needs SSL
    import ssl
    _ctx = ssl.create_default_context()
    _ctx.check_hostname = False
    _ctx.verify_mode = ssl.CERT_NONE
    _args = {"ssl": _ctx}
engine = create_engine(_url, connect_args=_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Student(Base):
    __tablename__ = "create_account_student"
    __table_args__ = (
        UniqueConstraint("college", "department", "division", "roll_number", name="uq_student_roll"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    college: Mapped[str] = mapped_column(String(150))
    department: Mapped[str] = mapped_column(String(100))
    division: Mapped[str] = mapped_column(String(10))
    roll_number: Mapped[str] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Admin(Base):
    __tablename__ = "create_account_admin"
    __table_args__ = (UniqueConstraint("college", "employee_id", name="uq_admin_employee"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    employee_id: Mapped[str] = mapped_column(String(30))
    college: Mapped[str] = mapped_column(String(150))
    designation: Mapped[str] = mapped_column(String(50))
    departments: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    phone: Mapped[str] = mapped_column(String(20), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class StudentLogin(Base):
    """One row per student: how many times the student logged in, and when last.

    Only successful logins are counted. The password is never stored here.
    """

    __tablename__ = "login_student"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("create_account_student.id"), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255))
    identifier: Mapped[str] = mapped_column(String(255))  # what was typed in the login field last time
    login_count: Mapped[int] = mapped_column(Integer, default=0)
    first_login_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    last_login_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class AdminLogin(Base):
    """One row per admin: how many times the admin logged in, and when last."""

    __tablename__ = "login_admin"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_id: Mapped[int] = mapped_column(ForeignKey("create_account_admin.id"), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255))
    identifier: Mapped[str] = mapped_column(String(255))  # what was typed in the login field last time
    login_count: Mapped[int] = mapped_column(Integer, default=0)
    first_login_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    last_login_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class LessonFile(Base):
    """A file an admin uploaded for one division. The file itself is on disk, this row describes it."""

    __tablename__ = "lesson_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_id: Mapped[int] = mapped_column(ForeignKey("create_account_admin.id"))
    department: Mapped[str] = mapped_column(String(10))
    year: Mapped[str] = mapped_column(String(10))
    division: Mapped[str] = mapped_column(String(10))
    original_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(60))  # random name on disk, never the user's name
    content_type: Mapped[str] = mapped_column(String(100), default="")
    size_bytes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="uploaded")  # uploaded or explained
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)  # the AI lesson, saved as JSON text
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()