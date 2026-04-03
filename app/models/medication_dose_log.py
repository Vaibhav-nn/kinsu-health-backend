"""Medication dose-event ORM model for adherence tracking."""

from datetime import date, datetime, time, timezone
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MedicationDoseLog(Base):
    """Represents a medication dose occurrence and its final status."""

    __tablename__ = "medication_dose_logs"

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
    medication_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("medications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scheduled_for: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    scheduled_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    taken_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
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

    medication: Mapped["Medication"] = relationship("Medication", back_populates="dose_logs")

