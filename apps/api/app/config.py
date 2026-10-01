import logging

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_FORECAST_DEFAULT = "https://api.open-meteo.com/v1/forecast"
_AIR_DEFAULT = "https://air-quality-api.open-meteo.com/v1/air-quality"


class Settings(BaseSettings):
    """Config from environment variables. No secrets ever hardcoded here (rule #3)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/za_oknem"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[str] = ["http://localhost:8081", "http://localhost:19006"]

    # ADR-022: Open-Meteo provider endpoints + key live in env, never in code. Defaults =
    # Free (non-commercial) hosts. Commercial plan = env only: customer-api.open-meteo.com,
    # customer-air-quality-api.open-meteo.com and OPEN_METEO_API_KEY (sent as `apikey`).
    open_meteo_forecast_base_url: str = _FORECAST_DEFAULT
    open_meteo_air_quality_base_url: str = _AIR_DEFAULT
    # repr=False: the key must not show up in repr(settings) / debug dumps.
    open_meteo_api_key: str | None = Field(default=None, repr=False)
    # Free tier cap (source-registry); raise it with a commercial plan (ADR-022).
    open_meteo_daily_call_limit: int = Field(default=10_000, gt=0)

    @field_validator("open_meteo_api_key", mode="before")
    @classmethod
    def _blank_key_is_none(cls, v: object) -> object:
        return (v.strip() or None) if isinstance(v, str) else v

    @field_validator(
        "open_meteo_forecast_base_url", "open_meteo_air_quality_base_url", mode="before"
    )
    @classmethod
    def _strip_url(cls, v: object) -> object:
        return v.strip() if isinstance(v, str) else v

    @model_validator(mode="after")
    def _open_meteo_urls(self) -> "Settings":
        # An empty env value (e.g. `OPEN_METEO_..._BASE_URL=` in a compose env file) means
        # "use the default", not "override with an empty string".
        if not self.open_meteo_forecast_base_url:
            self.open_meteo_forecast_base_url = _FORECAST_DEFAULT
        if not self.open_meteo_air_quality_base_url:
            self.open_meteo_air_quality_base_url = _AIR_DEFAULT
        if self.open_meteo_api_key:  # never send a key over plain http
            for url in (self.open_meteo_forecast_base_url, self.open_meteo_air_quality_base_url):
                if not url.startswith("https://"):
                    raise ValueError("OPEN_METEO_*_BASE_URL must be https:// when a key is set")
        return self


settings = Settings()


def warn_if_open_meteo_host_unusual() -> None:
    """Called once at scheduler / CLI start (ADR-022). Soft check only: the
    `customer-` host name is derived from the docs' prefix rule, not verified."""
    if not settings.open_meteo_api_key:
        return
    for url in (settings.open_meteo_forecast_base_url, settings.open_meteo_air_quality_base_url):
        host = url.split("//", 1)[-1].split("/", 1)[0]
        if not host.startswith("customer-"):
            logger.warning(
                "OPEN_METEO_API_KEY is set but host %s does not start with 'customer-' "
                "(commercial hosts do, ADR-022) - check the configuration",
                host,
            )
