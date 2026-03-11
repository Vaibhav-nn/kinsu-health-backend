from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Kinsu Health API"
    database_url: str = "postgresql+asyncpg://vatiwari@localhost:5432/kinsu_health"
    base_url: str = "http://localhost:8000"
    
    storage_backend: str = "local"
    file_storage_path: str = "./uploads"
    
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket_name: str = "kinsu-health-vault"
    s3_presigned_url_expiration: int = 3600


settings = Settings()
