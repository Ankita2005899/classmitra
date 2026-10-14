"""Database connection and the two tables: students and admins.

MySQL (Workbench) for real work, or a local SQLite file if DATABASE_URL is empty.
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .config import get_settings

_url = get_settings().database_url
_args = {"check_same_thread": False} if _url.startswith("sqlite") else {}
engine = create_engine(_url, connect_args=_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Student(Base):
    __tablename__ = "students"
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
    __tablename__ = "admins"
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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
