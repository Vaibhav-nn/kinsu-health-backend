"""User ORM model.

The Firebase UID is stored as a unique indexed column, while the internal
auto-increment `id` serves as the primary key for foreign-key relationships
in other tables.
"""

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Date, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    """Represents an authenticated user in the system."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    firebase_uid: Mapped[str] = mapped_column(
        String(128), unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    photo_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    blood_group: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    height_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    profession: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    health_goals: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    consent_accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    onboarding_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    auth_provider: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────
    vital_logs: Mapped[list["VitalLog"]] = relationship(
        "VitalLog",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    chronic_symptoms: Mapped[list["ChronicSymptom"]] = relationship(
        "ChronicSymptom",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    illness_episodes: Mapped[list["IllnessEpisode"]] = relationship(
        "IllnessEpisode",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    medications: Mapped[list["Medication"]] = relationship(
        "Medication",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    reminders: Mapped[list["Reminder"]] = relationship(
        "Reminder",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    home_preference: Mapped[Optional["HomePreference"]] = relationship(
        "HomePreference",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    home_notifications: Mapped[list["HomeNotification"]] = relationship(
        "HomeNotification",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    family_members: Mapped[list["FamilyMember"]] = relationship(
        "FamilyMember",
        back_populates="owner",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}')>"
