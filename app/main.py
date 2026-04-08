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
from app.core.database import engine, Base

# ── Import routers (also registers ORM models with Base.metadata) ─────────
from app.api.v1.auth import router as auth_router
from app.api.v1.vitals import router as vitals_router
from app.api.v1.symptoms import router as symptoms_router
from app.api.v1.illness import router as illness_router
from app.api.v1.medications import router as medications_router
from app.api.v1.reminders import router as reminders_router
from app.api.v1.homescreen import router as homescreen_router
from app.api.v1.appointments import router as appointments_router
from app.api.v1.exercise import router as exercise_router
from app.api.v1.vault import router as vault_router
from app.api.v1.family import router as family_router

# ── Bootstrap DB — creates tables that don't exist yet ────────────────────
Base.metadata.create_all(bind=engine, checkfirst=True)


# ── Lifespan ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown events."""
    initialize_firebase()
    print(f"✅ App started. DB: {settings.DATABASE_URL}")
    yield


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
local_dev_origin_regex = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
allow_origin_regex = (settings.CORS_ORIGIN_REGEX or "").strip() or local_dev_origin_regex

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_origin_regex=allow_origin_regex,
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
app.include_router(appointments_router, prefix=settings.API_V1_PREFIX)
app.include_router(exercise_router, prefix=settings.API_V1_PREFIX)
app.include_router(vault_router, prefix=settings.API_V1_PREFIX)
app.include_router(family_router, prefix=settings.API_V1_PREFIX)

# Keep legacy vault paths available at /vault/* as well.
app.include_router(vault_router)


# ── Health Check ─────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root() -> dict:
    """Root health check endpoint."""
    return {"status": "healthy", "service": settings.PROJECT_NAME, "v": "2"}


@app.get("/debug/db", tags=["Health"])
async def debug_db() -> dict:
    """Debug endpoint: returns DB URL and table list."""
    from sqlalchemy import inspect as sa_inspect, text
    from app.core.database import engine
    tables = sa_inspect(engine).get_table_names()
    return {"database_url": settings.DATABASE_URL, "tables": tables}
