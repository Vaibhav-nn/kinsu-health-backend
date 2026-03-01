from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "Kinsu Health API"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/kinsu_health"


settings = Settings()
