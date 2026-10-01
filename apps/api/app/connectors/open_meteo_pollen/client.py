"""HTTP client for the Open-Meteo Air Quality API, pollen variables only (ADR-020).

Open-Meteo relays the CAMS European air-quality forecast (cams_europe domain).
Endpoint, parameter names and variable names are per the official documentation
(open-meteo.com/en/docs/air-quality-api); the response shape has NOT been seen
against a live sample in this sandbox (egress to air-quality-api.open-meteo.com is
blocked) - parser.py validates the shape and fails loudly instead of guessing.

The request carries a geo_area centroid (ADR-001/ADR-005), never a user's position.
"""

from collections.abc import Callable

import httpx

BASE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
TIMEOUT = httpx.Timeout(10.0, connect=5.0)

# Master Plan §6 MVP species: olcha, brzoza, trawy, bylica, ambrozja. Olive is also
# offered by the source but is not an MVP species for Poland - deliberately not asked.
HOURLY_PARAMS = "alder_pollen,birch_pollen,grass_pollen,mugwort_pollen,ragweed_pollen"
# Pollen exists only in the European domain ("Only available in Europe during pollen
# season with 4 days forecast"); pinning it avoids a silent fallback to cams_global,
# which carries no pollen.
DOMAIN = "cams_europe"
# CAMS Europe forecasts 4 days ahead (docs); the default 5 would only add a null day.
FORECAST_DAYS = 4


class OpenMeteoPollenApiError(Exception):
    """Raised when the Air Quality API returns an unexpected status or unparseable body."""


def fetch_pollen(
    latitude: float,
    longitude: float,
    *,
    on_attempt: Callable[[], None] | None = None,
) -> dict:
    """GET the hourly pollen forecast for one point. Timeout + a single retry (rule #5).
    `on_attempt` fires once per REAL outbound request, BEFORE it goes out (same
    reservation semantics as open_meteo.client.fetch_weather: overcounting one call
    beats losing a call the provider already billed)."""
    params: dict[str, str | float | int] = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": HOURLY_PARAMS,
        "domains": DOMAIN,
        "forecast_days": FORECAST_DAYS,
        "timezone": "UTC",
    }
    last_error: Exception | None = None
    for _attempt in range(2):
        if on_attempt is not None:
            on_attempt()
        try:
            response = httpx.get(BASE_URL, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
    raise OpenMeteoPollenApiError(
        f"GET {BASE_URL} ({latitude}, {longitude}) failed after retry: {last_error}"
    ) from last_error
