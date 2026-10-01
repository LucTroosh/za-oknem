from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Config from environment variables. No secrets ever hardcoded here (rule #3)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/za_oknem"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[str] = ["http://localhost:8081", "http://localhost:19006"]

    # ADR-022: Open-Meteo provider endpoints + key live in env, never in code. Defaults =
    # Free (non-commercial) hosts. Commercial plan = env only: customer-api.open-meteo.com,
    # customer-air-quality-api.open-meteo.com and OPEN_METEO_API_KEY (sent as `apikey`).
    open_meteo_forecast_base_url: str = "https://api.open-meteo.com/v1/forecast"
    open_meteo_air_quality_base_url: str = "https://air-quality-api.open-meteo.com/v1/air-quality"
    open_meteo_api_key: str | None = None


settings = Settings()
