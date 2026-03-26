"""Authentication endpoint — Firebase login with user upsert."""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, verify_firebase_token
from app.api.user_sync import upsert_user_from_decoded_token
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import (
    LoginResponse,
    UserConsentRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _calculate_age(dob: date | None) -> int | None:
    if dob is None:
        return None
    today = date.today()
    years = today.year - dob.year
    had_birthday = (today.month, today.day) >= (dob.month, dob.day)
    return years if had_birthday else years - 1


@router.post("/login", response_model=LoginResponse)
async def login(
    decoded_token: dict = Depends(verify_firebase_token),
    db: Session = Depends(get_db),
) -> LoginResponse:
    """Authenticate via Firebase and upsert the user record.

    Flow:
        1. Flutter sends Firebase ID token in Authorization header.
        2. ``verify_firebase_token`` validates it and extracts uid/email.
        3. This endpoint upserts the user in the local database.
        4. Returns the serialized user and a success message.
    """
    user, created = upsert_user_from_decoded_token(db, decoded_token)
    message = "User created successfully." if created else "Login successful."

    return LoginResponse(
        message=message,
        user=UserResponse.model_validate(user),
    )


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(user: User = Depends(get_current_user)) -> UserProfileResponse:
    """Fetch authenticated user profile and onboarding fields."""
    return UserProfileResponse(user=UserResponse.model_validate(user))


@router.put("/profile", response_model=UserProfileResponse)
async def update_profile(
    payload: UserProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    """Update onboarding/profile fields for the authenticated user."""
    update_data = payload.model_dump(exclude_unset=True)

    mark_onboarding_complete = update_data.pop("mark_onboarding_complete", False)
    for field_name, field_value in update_data.items():
        setattr(user, field_name, field_value)
    if "date_of_birth" in update_data:
        user.age = _calculate_age(user.date_of_birth)

    if mark_onboarding_complete and user.onboarding_completed_at is None:
        user.onboarding_completed_at = datetime.now(timezone.utc)

    db.add(user)
    db.commit()
    db.refresh(user)
    return UserProfileResponse(user=UserResponse.model_validate(user))


@router.post("/consent", response_model=UserProfileResponse)
async def accept_consent(
    payload: UserConsentRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    """Record legal consent acceptance timestamp."""
    if payload.accepted:
        user.consent_accepted_at = datetime.now(timezone.utc)
        db.add(user)
        db.commit()
        db.refresh(user)
    return UserProfileResponse(user=UserResponse.model_validate(user))
