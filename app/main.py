"""Kinsu Health API — FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.firebase import initialize_firebase
from app.config import settings
from app.db import init_db
from app.routers import vault

# ── Import routers ───────────────────────────────────────
from app.api.v1.auth import router as auth_router
from app.api.v1.vitals import router as vitals_router
from app.api.v1.symptoms import router as symptoms_router
from app.api.v1.illness import router as illness_router
from app.api.v1.medications import router as medications_router
from app.api.v1.reminders import router as reminders_router
from app.api.v1.homescreen import router as homescreen_router


# ── Lifespan ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown events.

    Startup:
        1. Initialize Firebase Admin SDK.
        2. Validate app startup dependencies.
    """
    # Startup
    initialize_firebase()
    print(f"✅ App started. Expecting migrated DB at: {settings.DATABASE_URL}")
    await init_db()
    yield
    # Shutdown (nothing to clean up for now)


# ── App ──────────────────────────────────────────────────

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Backend API for the Kinsu Health platform. "
        "Provides Firebase-authenticated endpoints for vitals logging, "
        "symptom tracking, illness episodes, medications, and reminders."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────

origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_origin_regex=settings.CORS_ORIGIN_REGEX or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────

app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(vitals_router, prefix=settings.API_V1_PREFIX)
app.include_router(symptoms_router, prefix=settings.API_V1_PREFIX)
app.include_router(illness_router, prefix=settings.API_V1_PREFIX)
app.include_router(medications_router, prefix=settings.API_V1_PREFIX)
app.include_router(reminders_router, prefix=settings.API_V1_PREFIX)
app.include_router(homescreen_router, prefix=settings.API_V1_PREFIX)
app.include_router(vault.router, prefix="/vault", tags=["vault"])



# ── Health Check ─────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root() -> dict:
    """Root health check endpoint."""
    return {"status": "healthy", "service": settings.PROJECT_NAME}
