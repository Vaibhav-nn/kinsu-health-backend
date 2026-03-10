import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class HealthRecord(Base):
    __tablename__ = "health_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    record_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    record_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(nullable=True)
    file_uploaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
