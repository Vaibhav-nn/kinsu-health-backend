"""FastAPI dependencies for Firebase token verification.

Usage in any endpoint:
    @router.get("/protected")
    def protected_route(user: User = Depends(get_current_user)):
        return {"email": user.email}
"""

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from firebase_admin import auth as firebase_auth

from app.core.database import get_db
from app.models.user import User


async def verify_firebase_token(
    authorization: str = Header(..., description="Bearer <Firebase ID Token>"),
) -> dict:
    """Validate the Firebase ID token from the Authorization header.

    Args:
        authorization: The raw Authorization header value.

    Returns:
        Decoded token dict containing at least ``uid`` and ``email``.

    Raises:
        HTTPException 401: If the token is missing, malformed, or invalid.
    """
    if not authorization.startswith("Bearer "):
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

    Raises:
        HTTPException 404: If the user has not completed login (no DB record).
    """
    firebase_uid: str = decoded_token.get("uid", "")

    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please call POST /api/v1/auth/login first.",
        )

    return user
