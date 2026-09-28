from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Config from environment variables. No secrets ever hardcoded here (rule #3)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/za_oknem"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[str] = ["http://localhost:8081", "http://localhost:19006"]


settings = Settings()
