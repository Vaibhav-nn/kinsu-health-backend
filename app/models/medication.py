"""Medication ORM model for tracking prescribed and active medications."""

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Medication(Base):
    """A medication entry with dosage, frequency, and prescribing info."""

    __tablename__ = "medications"
    __table_args__ = (
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_medications_valid_date_range",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    family_member_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("family_members.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    dosage: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="e.g. 500mg, 10ml"
    )
    frequency: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="once_daily, twice_daily, thrice_daily, as_needed, weekly",
    )
    route: Mapped[str] = mapped_column(
        String(32), nullable=False, default="oral",
        comment="oral, topical, injection, inhaled, sublingual",
    )

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="Null means ongoing"
    )
    prescribing_doctor: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    user: Mapped["User"] = relationship("User", back_populates="medications")
    family_member: Mapped[Optional["FamilyMember"]] = relationship("FamilyMember")
    reminders: Mapped[list["Reminder"]] = relationship(
        "Reminder",
        back_populates="medication",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Medication(id={self.id}, name='{self.name}')>"
