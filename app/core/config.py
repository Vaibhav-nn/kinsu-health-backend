"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the Kinsu Health backend.

    Values are loaded from a `.env` file or environment variables.
    Supports both SQLite and PostgreSQL databases, as well as local and S3 storage.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────
    PROJECT_NAME: str = "Kinsu Health API"
    API_V1_PREFIX: str = "/api/v1"
    BASE_URL: str = "http://127.0.0.1:8501"

    # ── Database ──────────────────────────────────────────
    # Default to async PostgreSQL; supports SQLite with sqlite+aiosqlite://
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/kinsu_health"

    # ── Firebase ──────────────────────────────────────────
    FIREBASE_CREDENTIALS_PATH: str = "./firebase-service-account.json"

    # ── CORS ──────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080,http://localhost:5173"
    CORS_ORIGIN_REGEX: str = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

    # ── Storage ───────────────────────────────────────────
    STORAGE_BACKEND: str = "local"  # "local" or "s3"
    FILE_STORAGE_PATH: str = "./uploads"

    # ── AWS S3 ────────────────────────────────────────────
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "kinsu-health-vault"
    S3_PRESIGNED_URL_EXPIRATION: int = 3600

    # ── Logging ───────────────────────────────────────────
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FORMAT: str = "development"  # "json" or "development"


settings = Settings()
