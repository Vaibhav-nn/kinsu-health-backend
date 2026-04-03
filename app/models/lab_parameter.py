"""Lab parameter result ORM model for vault trend views."""

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LabParameterResult(Base):
    """A structured lab measurement extracted or entered for a health record."""

    __tablename__ = "lab_parameter_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("health_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    family_member_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("family_members.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    parameter_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    parameter_label: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    reference_low: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reference_high: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

