"""Family-member ORM model for linked dependent profiles."""

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FamilyMember(Base):
    """A dependent profile linked under an authenticated owner account."""

    __tablename__ = "family_members"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "phone_e164", name="uq_family_owner_phone"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    phone_e164: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    relation: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
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

    owner: Mapped["User"] = relationship("User", back_populates="family_members")

    def __repr__(self) -> str:
        return f"<FamilyMember(id={self.id}, owner_user_id={self.owner_user_id}, name='{self.display_name}')>"
