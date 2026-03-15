from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class HealthRecord(Base):
    """Health record/document stored in the vault with optional file attachment."""

    __tablename__ = "health_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    record_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    record_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(nullable=True)
    file_uploaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

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
    user: Mapped["User"] = relationship("User", back_populates="health_records")

    def __repr__(self) -> str:
        return f"<HealthRecord(id={self.id}, title='{self.title}')>"
