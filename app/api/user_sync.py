"""Helpers to sync Firebase-authenticated users into local DB."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.user import User


def _email_from_token(decoded_token: dict, firebase_uid: str) -> str:
    """Resolve a stable email value from Firebase token payload."""
    email = (decoded_token.get("email") or "").strip()
    if email:
        return email
    # Fallback keeps DB constraints valid for providers/tokens without email.
    return f"{firebase_uid}@firebase.local"


def upsert_user_from_decoded_token(db: Session, decoded_token: dict) -> tuple[User, bool]:
    """Upsert and return the local user for a decoded Firebase token.

    Returns:
        tuple[user, created]
    """
    firebase_uid: str = (decoded_token.get("uid") or "").strip()
    if not firebase_uid:
        raise ValueError("Decoded token is missing 'uid'.")

    email = _email_from_token(decoded_token, firebase_uid)
    display_name: str | None = decoded_token.get("name")
    auth_provider: str | None = (
        (decoded_token.get("firebase") or {}).get("sign_in_provider")
    )
    now = datetime.now(timezone.utc)

    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()
    created = False
    should_commit = False

    if user is None:
        user = User(
            firebase_uid=firebase_uid,
            email=email,
            display_name=display_name,
            auth_provider=auth_provider,
            last_login_at=now,
        )
        db.add(user)
        created = True
        should_commit = True
    else:
        if user.email != email:
            user.email = email
            should_commit = True
        if display_name and user.display_name != display_name:
            user.display_name = display_name
            should_commit = True
        if auth_provider and user.auth_provider != auth_provider:
            user.auth_provider = auth_provider
            should_commit = True
        user.last_login_at = now
        should_commit = True

    if should_commit:
        db.commit()
        db.refresh(user)

    return user, created
