"""FastAPI dependencies for Firebase token verification.

Usage in any endpoint:
    @router.get("/protected")
    async def protected_route(user: User = Depends(get_current_user)):
        return {"email": user.email}
"""

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from firebase_admin import auth as firebase_auth

from app.core.database import get_db
from app.models.user import User
from app.api.user_sync import upsert_user_from_decoded_token
from app.core.logging import get_logger, user_id_var

logger = get_logger(__name__)


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
        logger.warning("Invalid authorization header format")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be 'Bearer <token>'.",
        )

    token = authorization.removeprefix("Bearer ").strip()

    try:
        decoded_token: dict = firebase_auth.verify_id_token(token)
        logger.debug(
            "Firebase token verified successfully",
            extra={"extra_fields": {"uid": decoded_token.get("uid")}},
        )
        return decoded_token
    except firebase_auth.ExpiredIdTokenError:
        logger.warning("Firebase token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase ID token has expired. Please re-authenticate.",
        )
    except firebase_auth.RevokedIdTokenError:
        logger.warning("Firebase token revoked")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase ID token has been revoked.",
        )
    except firebase_auth.InvalidIdTokenError:
        logger.warning("Invalid Firebase token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Firebase ID token.",
        )
    except Exception as e:
        logger.exception(
            "Firebase token validation failed",
            extra={"extra_fields": {"error": str(e)}},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate Firebase credentials.",
        )

    return decoded_token


async def get_current_user(
    decoded_token: dict = Depends(verify_firebase_token),
    db: AsyncSession = Depends(get_db),
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
    uid = decoded_token.get("uid")
    
    try:
        user, created = await upsert_user_from_decoded_token(db, decoded_token)
        
        # Set user context for logging
        user_id_var.set(str(user.id))
        
        if created:
            logger.info(
                "New user created from Firebase token",
                extra={"extra_fields": {"firebase_uid": uid, "email": user.email}},
            )
        else:
            logger.debug(
                "Existing user authenticated",
                extra={"extra_fields": {"firebase_uid": uid}},
            )
        
        return user
    except ValueError as e:
        logger.error(
            "Invalid Firebase token payload",
            extra={"extra_fields": {"firebase_uid": uid, "error": str(e)}},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase token payload is missing required user identity.",
        )
