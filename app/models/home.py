"""Homescreen ORM models for user preferences and notification feed."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class HomePreference(Base):
    """Stores persistent homescreen preferences for a user."""

    __tablename__ = "home_preferences"
    __table_args__ = (
        CheckConstraint(
            "theme_mode IN ('light', 'dark', 'system')",
            name="ck_home_preferences_theme_mode_values",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    theme_mode: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="system",
        comment="light, dark, system",
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
    user: Mapped["User"] = relationship("User", back_populates="home_preference")

    def __repr__(self) -> str:
        return f"<HomePreference(user_id={self.user_id}, theme_mode='{self.theme_mode}')>"


class HomeNotification(Base):
    """A homescreen notification item."""

    __tablename__ = "home_notifications"
    __table_args__ = (
        CheckConstraint(
            "is_read = FALSE OR read_at IS NOT NULL",
            name="ck_home_notifications_read_requires_timestamp",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    notification_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="general"
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    action_route: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationship ──────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="home_notifications")

    def __repr__(self) -> str:
        return f"<HomeNotification(id={self.id}, type='{self.notification_type}', read={self.is_read})>"
