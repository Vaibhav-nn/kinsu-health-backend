"""Pydantic schemas for user authentication."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


# ── Response Schemas ──────────────────────────────────────

class UserResponse(BaseModel):
    """Serialized user returned in API responses."""

    id: int
    firebase_uid: str
    email: str
    display_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Response for POST /auth/login."""

    message: str
    user: UserResponse
