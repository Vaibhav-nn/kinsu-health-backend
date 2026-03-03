"""ChronicSymptom ORM model for tracking ongoing symptoms."""

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ChronicSymptom(Base):
    """A chronic or recurring symptom being tracked by the user."""

    __tablename__ = "chronic_symptoms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    symptom_name: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="e.g. migraine, joint_pain, fatigue"
    )
    severity: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="1-10 scale"
    )
    frequency: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="daily, weekly, monthly, intermittent",
    )
    body_area: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="e.g. head, lower_back, chest"
    )
    triggers: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Comma-separated or JSON list of triggers"
    )

    first_noticed: Mapped[date] = mapped_column(Date, nullable=False)
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

    def __repr__(self) -> str:
        return f"<ChronicSymptom(id={self.id}, name='{self.symptom_name}')>"
