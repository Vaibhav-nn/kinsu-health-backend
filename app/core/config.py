"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for the Kinsu Health backend.

    Values are loaded from a `.env` file or environment variables.
    To migrate to PostgreSQL, simply change DATABASE_URL in your .env:
        DATABASE_URL=postgresql+psycopg2://user:pass@host/dbname
    """

    # ── Database ──────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./kinsu.db"

    # ── Firebase ──────────────────────────────────────────
    FIREBASE_CREDENTIALS_PATH: str = "./firebase-service-account.json"

    # ── CORS ──────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"

    # ── API ───────────────────────────────────────────────
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Kinsu Health API"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
