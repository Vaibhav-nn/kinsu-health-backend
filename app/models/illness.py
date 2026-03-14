"""IllnessEpisode and IllnessDetail ORM models.

An episode represents a distinct illness occurrence. Each episode can contain
multiple detail entries (symptoms, diagnoses, treatments, notes) to provide
a chronological, detailed view.
"""

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
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


class IllnessEpisode(Base):
    """A distinct illness occurrence with start/end dates and status."""

    __tablename__ = "illness_episodes"
    __table_args__ = (
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_illness_episodes_valid_date_range",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="Null means ongoing"
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active",
        comment="active, recovered, chronic",
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

    # ── Relationship ──────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="illness_episodes")
    details: Mapped[list["IllnessDetail"]] = relationship(
        "IllnessDetail",
        back_populates="episode",
        cascade="all, delete-orphan",
        order_by="IllnessDetail.recorded_at",
    )

    def __repr__(self) -> str:
        return f"<IllnessEpisode(id={self.id}, title='{self.title}')>"


class IllnessDetail(Base):
    """A detail entry (symptom, diagnosis, treatment, note) within an episode."""

    __tablename__ = "illness_details"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    episode_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("illness_episodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    detail_type: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="symptom, diagnosis, treatment, note",
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationship ──────────────────────────────────────
    episode: Mapped["IllnessEpisode"] = relationship(
        "IllnessEpisode", back_populates="details"
    )

    def __repr__(self) -> str:
        return f"<IllnessDetail(id={self.id}, type='{self.detail_type}')>"
