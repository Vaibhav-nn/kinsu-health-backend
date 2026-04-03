"""Pydantic schemas for family-member linking and account switching."""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


def _normalize_phone(value: str) -> str:
    raw = value.strip().replace(" ", "")
    if not raw:
        return raw
    if raw.startswith("+"):
        return "+" + "".join(ch for ch in raw[1:] if ch.isdigit())
    return "+" + "".join(ch for ch in raw if ch.isdigit())


class FamilyMemberCreate(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=256)
    phone_e164: str = Field(..., min_length=8, max_length=32)
    relation: Optional[str] = Field(default=None, max_length=64)
    date_of_birth: Optional[date] = None
    blood_group: Optional[str] = Field(default=None, max_length=8)
    health_conditions: Optional[list[str]] = None
    notes: Optional[str] = None

    @field_validator("phone_e164")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        normalized = _normalize_phone(value)
        if not normalized.startswith("+") or len(normalized) < 8:
            raise ValueError("phone_e164 must be a valid E.164-style number.")
        return normalized


class FamilyMemberUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=256)
    phone_e164: Optional[str] = Field(default=None, min_length=8, max_length=32)
    relation: Optional[str] = Field(default=None, max_length=64)
    date_of_birth: Optional[date] = None
    blood_group: Optional[str] = Field(default=None, max_length=8)
    health_conditions: Optional[list[str]] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("phone_e164")
    @classmethod
    def validate_phone(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = _normalize_phone(value)
        if not normalized.startswith("+") or len(normalized) < 8:
            raise ValueError("phone_e164 must be a valid E.164-style number.")
        return normalized


class FamilyMemberResponse(BaseModel):
    id: int
    display_name: str
    phone_e164: str
    relation: Optional[str] = None
    date_of_birth: Optional[date] = None
    blood_group: Optional[str] = None
    health_conditions: Optional[list[str]] = None
    notes: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FamilyDashboardCard(BaseModel):
    profile_type: Literal["self", "family_member"]
    profile_id: Optional[int] = None
    display_name: str
    relation: str
    age: Optional[int] = None
    blood_group: Optional[str] = None
    initials: str
    health_conditions: list[str] = Field(default_factory=list)
    record_count: int = 0
    medication_count: int = 0
    last_activity: str = "No activity yet"
    is_active_context: bool = False


class CaregiverPermissionResponse(BaseModel):
    permission_key: str
    label: str
    description: str
    is_enabled: bool


class CaregiverPermissionUpdate(BaseModel):
    permission_key: str
    is_enabled: bool


class AccountProfileOption(BaseModel):
    profile_type: Literal["self", "family_member"]
    profile_id: Optional[int] = None
    display_name: str
    subtitle: Optional[str] = None
