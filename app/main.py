"""Kinsu Health API — FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload --port 8000
"""

import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import time

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.firebase import initialize_firebase
from app.core.database import init_db
from app.core.logging import (
    setup_logging,
    get_logger,
    request_id_var,
    user_id_var,
)

# ── Import routers ───────────────────────────────────────
from app.api.v1.auth import router as auth_router
from app.api.v1.vitals import router as vitals_router
from app.api.v1.symptoms import router as symptoms_router
from app.api.v1.illness import router as illness_router
from app.api.v1.medications import router as medications_router
from app.api.v1.reminders import router as reminders_router
from app.api.v1.homescreen import router as homescreen_router
from app.api.v1.vault import router as vault_router

# ── Logging Setup ────────────────────────────────────────
setup_logging(
    log_level=settings.LOG_LEVEL,
    use_json=(settings.LOG_FORMAT == "json"),
)
logger = get_logger(__name__)

# ── Lifespan ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown events.

    Startup:
        1. Initialize Firebase Admin SDK.
        2. Validate app startup dependencies.
    """
    # Startup
    logger.info(
        "Starting Kinsu Health API",
        extra={
            "extra_fields": {
                "project_name": settings.PROJECT_NAME,
                "database_url": settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL,
                "storage_backend": settings.STORAGE_BACKEND,
                "log_level": settings.LOG_LEVEL,
            }
        },
    )
    
    try:
        initialize_firebase()
        logger.info("Firebase initialized successfully")
        
        await init_db()
        logger.info("Database initialized successfully")
        
        logger.info("Application startup complete")
    except Exception as e:
        logger.exception("Failed to start application", extra={"extra_fields": {"error": str(e)}})
        raise
    
    yield
    
    # Shutdown
    logger.info("Application shutting down")


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


# ── Logging Middleware ───────────────────────────────────

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests and responses with timing."""

    async def dispatch(self, request: Request, call_next):
        # Generate unique request ID
        req_id = str(uuid.uuid4())
        request_id_var.set(req_id)
        
        # Log incoming request
        logger.info(
            "Incoming request",
            extra={
                "extra_fields": {
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": str(request.query_params),
                    "client_host": request.client.host if request.client else None,
                }
            },
        )
        
        # Process request and measure time
        start_time = time.time()
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            
            # Log successful response
            logger.info(
                "Request completed",
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "duration_ms": round(duration_ms, 2),
                    }
                },
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = req_id
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.exception(
                "Request failed",
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": round(duration_ms, 2),
                        "error": str(e),
                    }
                },
            )
            raise
        finally:
            # Clear context variables
            request_id_var.set(None)
            user_id_var.set(None)


app.add_middleware(LoggingMiddleware)

# ── Routers ──────────────────────────────────────────────

app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(vitals_router, prefix=settings.API_V1_PREFIX)
app.include_router(symptoms_router, prefix=settings.API_V1_PREFIX)
app.include_router(illness_router, prefix=settings.API_V1_PREFIX)
app.include_router(medications_router, prefix=settings.API_V1_PREFIX)
app.include_router(reminders_router, prefix=settings.API_V1_PREFIX)
app.include_router(homescreen_router, prefix=settings.API_V1_PREFIX)
app.include_router(vault_router, prefix="/vault", tags=["vault"])



# ── Health Check ─────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root() -> dict:
    """Root health check endpoint."""
    logger.debug("Health check endpoint called")
    return {"status": "healthy", "service": settings.PROJECT_NAME}
