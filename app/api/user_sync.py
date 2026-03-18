"""Helpers to sync Firebase-authenticated users into local DB."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.logging import get_logger

logger = get_logger(__name__)


def _email_from_token(decoded_token: dict, firebase_uid: str) -> str:
    """Resolve a stable email value from Firebase token payload."""
    email = (decoded_token.get("email") or "").strip()
    if email:
        return email
    # Fallback keeps DB constraints valid for providers/tokens without email.
    fallback = f"{firebase_uid}@firebase.local"
    logger.debug(
        "Using fallback email for Firebase user",
        extra={"extra_fields": {"firebase_uid": firebase_uid, "fallback_email": fallback}},
    )
    return fallback


async def upsert_user_from_decoded_token(db: AsyncSession, decoded_token: dict) -> tuple[User, bool]:
    """Upsert and return the local user for a decoded Firebase token.

    Returns:
        tuple[user, created]
    """
    firebase_uid: str = (decoded_token.get("uid") or "").strip()
    if not firebase_uid:
        logger.error("Decoded token missing 'uid'")
        raise ValueError("Decoded token is missing 'uid'.")

    email = _email_from_token(decoded_token, firebase_uid)
    display_name: str | None = decoded_token.get("name")

    logger.debug(
        "Upserting user from Firebase token",
        extra={"extra_fields": {"firebase_uid": firebase_uid, "email": email}},
    )

    result = await db.execute(
        select(User).where(
            (User.firebase_uid == firebase_uid) | (User.email == email)
        )
    )
    user = result.scalar_one_or_none()
    created = False
    should_flush = False

    if user is None:
        user = User(
            firebase_uid=firebase_uid,
            email=email,
            display_name=display_name,
        )
        db.add(user)
        created = True
        should_flush = True
        logger.info(
            "Creating new user from Firebase token",
            extra={"extra_fields": {"firebase_uid": firebase_uid, "email": email}},
        )
    else:
        if user.firebase_uid != firebase_uid:
            logger.info(
                "Updating user Firebase UID",
                extra={"extra_fields": {"user_id": str(user.id), "old_uid": user.firebase_uid, "new_uid": firebase_uid}},
            )
            user.firebase_uid = firebase_uid
            should_flush = True
        if user.email != email:
            logger.info(
                "Updating user email",
                extra={"extra_fields": {"user_id": str(user.id), "old_email": user.email, "new_email": email}},
            )
            user.email = email
            should_flush = True
        if display_name and user.display_name != display_name:
            logger.debug(
                "Updating user display name",
                extra={"extra_fields": {"user_id": str(user.id), "new_display_name": display_name}},
            )
            user.display_name = display_name
            should_flush = True

    if should_flush:
        await db.flush()
        await db.refresh(user)

    return user, created
