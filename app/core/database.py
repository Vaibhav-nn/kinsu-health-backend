"""SQLAlchemy database engine, session factory, and declarative base.

Adapter Pattern: To switch from SQLite → PostgreSQL, change only the
DATABASE_URL in your .env file. No code changes required.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from typing import Generator

from app.core.config import settings


# ── Engine ────────────────────────────────────────────────
# SQLite requires check_same_thread=False for FastAPI's async workers.
# This kwarg is harmlessly ignored by PostgreSQL drivers.
connect_args: dict = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

# ── Session ───────────────────────────────────────────────
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Declarative Base ──────────────────────────────────────
class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# ── Dependency ────────────────────────────────────────────
def get_db() -> Generator:
    """FastAPI dependency that yields a database session.

    Usage:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
