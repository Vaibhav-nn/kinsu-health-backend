"""Reminder ORM model for scheduled health reminders."""

from datetime import datetime, time, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Reminder(Base):
    """A scheduled reminder, optionally linked to a medication."""

    __tablename__ = "reminders"
    __table_args__ = (
        CheckConstraint(
            "recurrence IN ('daily', 'weekly', 'monthly', 'once')",
            name="ck_reminders_recurrence_values",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(256), nullable=False)
    reminder_type: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="medication, appointment, checkup, custom",
    )
    linked_medication_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("medications.id", ondelete="SET NULL"),
        nullable=True,
    )

    scheduled_time: Mapped[time] = mapped_column(Time, nullable=False)
    recurrence: Mapped[str] = mapped_column(
        String(32), nullable=False, default="daily",
        comment="daily, weekly, monthly, once",
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
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
    user: Mapped["User"] = relationship("User", back_populates="reminders")
    medication: Mapped[Optional["Medication"]] = relationship(
        "Medication",
        back_populates="reminders",
    )

    def __repr__(self) -> str:
        return f"<Reminder(id={self.id}, title='{self.title}')>"
