"""Kinsu Health API — FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.core.firebase import initialize_firebase

# ── Import all models so Base.metadata knows about them ──
from app.models.user import User  # noqa: F401
from app.models.vital import VitalLog  # noqa: F401
from app.models.symptom import ChronicSymptom  # noqa: F401
from app.models.illness import IllnessEpisode, IllnessDetail  # noqa: F401
from app.models.medication import Medication  # noqa: F401
from app.models.reminder import Reminder  # noqa: F401

# ── Import routers ───────────────────────────────────────
from app.api.v1.auth import router as auth_router
from app.api.v1.vitals import router as vitals_router
from app.api.v1.symptoms import router as symptoms_router
from app.api.v1.illness import router as illness_router
from app.api.v1.medications import router as medications_router
from app.api.v1.reminders import router as reminders_router


# ── Lifespan ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown events.

    Startup:
        1. Initialize Firebase Admin SDK.
        2. Create all database tables (if they don't exist).
    """
    # Startup
    initialize_firebase()
    Base.metadata.create_all(bind=engine)
    print(f"✅ Database tables created. URL: {settings.DATABASE_URL}")
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


# ── Health Check ─────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root() -> dict:
    """Root health check endpoint."""
    return {"status": "healthy", "service": settings.PROJECT_NAME}
