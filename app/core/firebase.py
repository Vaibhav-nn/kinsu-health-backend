"""Firebase Admin SDK initialization.

Called once during application startup via the FastAPI lifespan handler.
"""

import os
from typing import Optional
import firebase_admin
from firebase_admin import credentials

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


_firebase_app: Optional[firebase_admin.App] = None


def initialize_firebase() -> None:
    """Initialize the Firebase Admin SDK with service account credentials.

    Skips initialization if:
    - Already initialized.
    - Credentials file does not exist (useful for local dev without Firebase).
    """
    global _firebase_app

    if _firebase_app is not None:
        logger.debug("Firebase already initialized, skipping")
        return

    cred_path = settings.FIREBASE_CREDENTIALS_PATH
    
    logger.info("Initializing Firebase Admin SDK", extra={"extra_fields": {"credentials_path": cred_path}})

    if not os.path.exists(cred_path):
        logger.warning(
            "Firebase credentials not found, auth will not work",
            extra={"extra_fields": {"expected_path": cred_path}},
        )
        return

    try:
        cred = credentials.Certificate(cred_path)
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully")
    except Exception as e:
        logger.exception(
            "Failed to initialize Firebase Admin SDK",
            extra={"extra_fields": {"credentials_path": cred_path, "error": str(e)}},
        )
        raise
