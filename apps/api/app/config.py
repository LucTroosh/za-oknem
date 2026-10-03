import logging
from datetime import date

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
    # ADR-029: a place-based area stops being polled after this many days without a
    # fresh activation (`POST /places/{id}/activate`); keeps the Open-Meteo budget bounded.
    place_activation_ttl_days: int = Field(default=7, gt=0)

    # ADR-032: the seven new GIOŚ datasets (dane.gios.gov.pl). They publish no rate limit or SLA
    # (source-registry: UNKNOWN), so every value here is OUR OWN bound, not a provider limit.
    gios_open_base_url: str = "https://dane.gios.gov.pl/api"
    gios_open_min_interval_seconds: float = Field(default=5.0, ge=0)  # per service, whole process
    gios_open_connect_timeout_seconds: float = Field(default=5.0, gt=0)
    gios_open_read_timeout_seconds: float = Field(default=20.0, gt=0)
    gios_open_max_retries: int = Field(default=2, ge=0, le=5)  # retries AFTER the first attempt
    gios_open_page_size: int = Field(default=50, ge=1, le=50)  # spec maximum is 50 (per operation)
    gios_open_max_pages: int = Field(default=2000, gt=0)  # safety valve, not a provider limit
    # A staging snapshot older than this is a dead run (crash): its lock may be taken over.
    gios_open_lock_ttl_minutes: int = Field(default=360, gt=0)

    # Air (current GIOŚ API, getData): values requested per sensor (spec: default 20, max 500).
    # Values are hourly and the source keeps only ~66 h per sensor (observed 2026-10-03), so this
    # is a ceiling, not a promise. Still ONE request per sensor (portal terms bound the count).
    gios_data_size: int = Field(default=100, ge=1, le=500)
    # Rollout after migration 0019; independent of measurement ingestion.
    gios_provider_index_enabled: bool = False

    # ADR-032: per-section switches for "Twoja okolica" (default off: a section is shown only after
    # its source passed the operator check). Noise: nearest measurement point within the radius.
    neighborhood_noise_enabled: bool = False
    neighborhood_noise_max_km: float = Field(default=10.0, gt=0, le=50)
    # "No measurement point nearby" is claimed only when EVERY category x voivodeship has an active
    # import whose date filter spans this whole range (a single year would miss older points).
    # Widen it only together with a re-import over the wider range.
    neighborhood_noise_coverage_from: date = date(2015, 1, 1)
    neighborhood_noise_coverage_to: date = date(2026, 12, 31)

    @field_validator("gios_open_base_url", mode="before")
    @classmethod
    def _gios_open_base_url(cls, v: object) -> object:
        return v.strip().rstrip("/") if isinstance(v, str) else v

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
    def _gios_open_https(self) -> "Settings":
        if not self.gios_open_base_url.startswith("https://"):
            raise ValueError("GIOS_OPEN_BASE_URL must be https://")
        return self

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
