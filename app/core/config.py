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
    CORS_ORIGIN_REGEX: str = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

    # ── API ───────────────────────────────────────────────
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Kinsu Health API"
    BASE_URL: str = "http://127.0.0.1:8000"

    # ── Vault Storage ─────────────────────────────────────
    STORAGE_BACKEND: str = "local"
    FILE_STORAGE_PATH: str = "./uploads"

    # ── AWS / S3 ──────────────────────────────────────────
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "kinsu-health-vault"
    S3_PRESIGNED_URL_EXPIRATION: int = 3600

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
