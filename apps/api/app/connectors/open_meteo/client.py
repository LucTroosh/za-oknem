"""HTTP client for the Open-Meteo forecast API (current weather).

Per docs/data/source-registry.md: shape is per official documentation
(open-meteo.com/en/docs) but NOT confirmed against a live sample in this
sandbox (api.open-meteo.com is robots.txt-blocked for this session's fetch
tools). parser.py validates the shape and fails loudly rather than guessing.

Rate limit (600/min, source registry) is far above our need (a handful of
geo_areas every 3h per ADR-004) — no throttling required, unlike GIOŚ.
"""

import httpx

BASE_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = httpx.Timeout(10.0, connect=5.0)

# Fields for "current conditions" — matches WeatherSnapshot.param_code values.
CURRENT_PARAMS = "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"


class OpenMeteoApiError(Exception):
    """Raised when Open-Meteo returns an unexpected status or unparseable body."""


def fetch_current(latitude: float, longitude: float) -> dict:
    """GET current weather for one point. Single retry on failure (rule #5)."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": CURRENT_PARAMS,
        "timezone": "UTC",
    }
    last_error: Exception | None = None
    for _attempt in range(2):
        try:
            response = httpx.get(BASE_URL, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
    raise OpenMeteoApiError(
        f"GET {BASE_URL} ({latitude}, {longitude}) failed after retry: {last_error}"
    ) from last_error
