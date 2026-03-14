"""VitalLog ORM model for recording health vital readings."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class VitalLog(Base):
    """A single vital-sign reading (heart rate, BP, SpO2, etc.)."""

    __tablename__ = "vital_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    vital_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
        comment="e.g. heart_rate, blood_pressure, spo2, temperature, weight",
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    value_secondary: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="e.g. diastolic reading for blood_pressure"
    )
    unit: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="e.g. bpm, mmHg, %, °C, kg"
    )

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationship ──────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="vital_logs")

    def __repr__(self) -> str:
        return f"<VitalLog(id={self.id}, type='{self.vital_type}', value={self.value})>"
