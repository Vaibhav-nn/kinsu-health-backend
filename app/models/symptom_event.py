"""Symptom event ORM model for quick symptom logging and trend summaries."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SymptomEvent(Base):
    """A single symptom occurrence/event."""

    __tablename__ = "symptom_events"

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
    symptom_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    severity: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

