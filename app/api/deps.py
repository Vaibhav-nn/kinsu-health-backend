"""FastAPI dependencies for Firebase token verification.

Usage in any endpoint:
    @router.get("/protected")
    def protected_route(user: User = Depends(get_current_user)):
        return {"email": user.email}
"""

from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from firebase_admin import auth as firebase_auth

from app.core.config import settings
from app.core.database import get_db
from app.models.family import FamilyMember
from app.models.user import User
from app.api.user_sync import upsert_user_from_decoded_token


async def verify_firebase_token(
    authorization: Optional[str] = Header(
        default=None, description="Bearer <Firebase ID Token>"
    ),
) -> dict:
    """Validate the Firebase ID token from the Authorization header.

    Args:
        authorization: The raw Authorization header value.

    Returns:
        Decoded token dict containing at least ``uid`` and ``email``.

    Raises:
        HTTPException 401: If the token is missing, malformed, or invalid.
    """
    if settings.AUTH_BYPASS:
        return {
            "uid": settings.AUTH_BYPASS_UID,
            "email": settings.AUTH_BYPASS_EMAIL,
            "name": settings.AUTH_BYPASS_NAME,
            "firebase": {"sign_in_provider": "demo_bypass"},
        }

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be 'Bearer <token>'.",
        )

    token = authorization.removeprefix("Bearer ").strip()

    try:
        decoded_token: dict = firebase_auth.verify_id_token(token)
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase ID token has expired. Please re-authenticate.",
        )
    except firebase_auth.RevokedIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase ID token has been revoked.",
        )
    except firebase_auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Firebase ID token.",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate Firebase credentials.",
        )

    return decoded_token


async def get_current_user(
    decoded_token: dict = Depends(verify_firebase_token),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated Firebase user to an internal User record.

    Args:
        decoded_token: The validated Firebase token payload.
        db: SQLAlchemy database session.

    Returns:
        The ``User`` ORM object for the authenticated user.

    Notes:
        The user is auto-upserted on first authenticated request.
    """
    try:
        user, _created = upsert_user_from_decoded_token(db, decoded_token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase token payload is missing required user identity.",
        )

    return user


@dataclass(frozen=True)
class ProfileScope:
    """Resolved data scope (self or linked family member)."""

    family_member_id: Optional[int]
    profile_label: str
    profile_type: str


async def get_profile_scope(
    x_profile_id: Optional[str] = Header(default=None, alias="X-Profile-Id"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileScope:
    """Resolve optional profile context from the request header.

    Defaults to self profile when header is missing or blank.
    """
    raw = (x_profile_id or "").strip()
    if not raw:
        return ProfileScope(
            family_member_id=None,
            profile_label=user.display_name or user.email,
            profile_type="self",
        )
    if raw.lower() == "self":
        return ProfileScope(
            family_member_id=None,
            profile_label=user.display_name or user.email,
            profile_type="self",
        )

    try:
        family_member_id = int(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Profile-Id must be a valid integer family member id.",
        ) from exc

    member = (
        db.query(FamilyMember)
        .filter(
            FamilyMember.id == family_member_id,
            FamilyMember.owner_user_id == user.id,
            FamilyMember.is_active.is_(True),
        )
        .first()
    )
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family member profile not found for this account.",
        )

    return ProfileScope(
        family_member_id=member.id,
        profile_label=member.display_name,
        profile_type="family_member",
    )
