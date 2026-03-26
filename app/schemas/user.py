"""Pydantic schemas for user authentication and onboarding profile data."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    """Serialized user returned in API responses."""

    id: int
    firebase_uid: str
    email: str
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    age: Optional[int] = None
    blood_group: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    profession: Optional[str] = None
    health_goals: Optional[list[str]] = None
    consent_accepted_at: Optional[datetime] = None
    onboarding_completed_at: Optional[datetime] = None
    auth_provider: Optional[str] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Response for POST /auth/login."""

    message: str
    user: UserResponse


class UserProfileUpdateRequest(BaseModel):
    """Profile data captured from onboarding and account settings."""

    display_name: Optional[str] = Field(default=None, max_length=256)
    photo_url: Optional[str] = Field(default=None, max_length=1024)
    gender: Optional[str] = Field(default=None, max_length=32)
    date_of_birth: Optional[date] = None
    blood_group: Optional[str] = Field(default=None, max_length=8)
    height_cm: Optional[float] = Field(default=None, ge=0, le=250)
    weight_kg: Optional[float] = Field(default=None, ge=0, le=200)
    profession: Optional[str] = Field(default=None, max_length=128)
    health_goals: Optional[list[str]] = None
    mark_onboarding_complete: bool = False


class UserConsentRequest(BaseModel):
    """Consent acknowledgement payload."""

    accepted: bool = True


class UserProfileResponse(BaseModel):
    """Profile details for authenticated user."""

    user: UserResponse
