"""Authentication endpoint — Firebase login with user upsert."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import verify_firebase_token
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import LoginResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


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
    firebase_uid: str = decoded_token["uid"]
    email: str = decoded_token.get("email", "")
    display_name: str | None = decoded_token.get("name")

    # ── Upsert logic ─────────────────────────────────────
    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()

    if user is None:
        # First login — create the user
        user = User(
            firebase_uid=firebase_uid,
            email=email,
            display_name=display_name,
        )
        db.add(user)
        message = "User created successfully."
    else:
        # Returning user — update fields if changed
        if user.email != email:
            user.email = email
        if display_name and user.display_name != display_name:
            user.display_name = display_name
        message = "Login successful."

    db.commit()
    db.refresh(user)

    return LoginResponse(
        message=message,
        user=UserResponse.model_validate(user),
    )
