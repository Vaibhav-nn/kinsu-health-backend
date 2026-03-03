"""Firebase Admin SDK initialization.

Called once during application startup via the FastAPI lifespan handler.
"""

import os
import firebase_admin
from firebase_admin import credentials

from app.core.config import settings


_firebase_app: firebase_admin.App | None = None


def initialize_firebase() -> None:
    """Initialize the Firebase Admin SDK with service account credentials.

    Skips initialization if:
    - Already initialized.
    - Credentials file does not exist (useful for local dev without Firebase).
    """
    global _firebase_app

    if _firebase_app is not None:
        return

    cred_path = settings.FIREBASE_CREDENTIALS_PATH

    if not os.path.exists(cred_path):
        print(
            f"⚠️  Firebase credentials not found at '{cred_path}'. "
            "Firebase auth will not work. Place your service account JSON there."
        )
        return

    cred = credentials.Certificate(cred_path)
    _firebase_app = firebase_admin.initialize_app(cred)
    print("✅ Firebase Admin SDK initialized successfully.")
