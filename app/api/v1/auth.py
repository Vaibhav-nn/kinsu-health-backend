"""Authentication endpoint — Firebase login with user upsert."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_firebase_token
from app.api.user_sync import upsert_user_from_decoded_token
from app.core.database import get_db
from app.schemas.user import LoginResponse, UserResponse
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(
    decoded_token: dict = Depends(verify_firebase_token),
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Authenticate via Firebase and upsert the user record.

    Flow:
        1. Flutter sends Firebase ID token in Authorization header.
        2. ``verify_firebase_token`` validates it and extracts uid/email.
        3. This endpoint upserts the user in the local database.
        4. Returns the serialized user and a success message.
    """
    uid = decoded_token.get("uid")
    email = decoded_token.get("email")
    
    logger.info(
        "Login attempt",
        extra={"extra_fields": {"firebase_uid": uid, "email": email}},
    )
    
    try:
        user, created = await upsert_user_from_decoded_token(db, decoded_token)
        message = "User created successfully." if created else "Login successful."
        
        logger.info(
            "Login successful",
            extra={
                "extra_fields": {
                    "user_id": str(user.id),
                    "firebase_uid": uid,
                    "created": created,
                }
            },
        )

        return LoginResponse(
            message=message,
            user=UserResponse.model_validate(user),
        )
    except Exception as e:
        logger.exception(
            "Login failed",
            extra={"extra_fields": {"firebase_uid": uid, "error": str(e)}},
        )
        raise
