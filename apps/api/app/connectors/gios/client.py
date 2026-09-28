"""HTTP client for the GIOŚ (Główny Inspektorat Ochrony Środowiska) air quality API.

Endpoint and rate limits confirmed against official docs (docs/data/source-registry.md):
https://api.gios.gov.pl/pjp-api/v1/rest/ — no API key. NOT verified against a live
response in this environment (sandbox has no network route to this host) — see the
"status" note in the Source Registry entry before relying on this in production.
"""

import httpx

BASE_URL = "https://api.gios.gov.pl/pjp-api/v1/rest"
TIMEOUT = httpx.Timeout(10.0, connect=5.0)


class GiosApiError(Exception):
    """Raised when GIOŚ returns an unexpected status or unparseable body."""


def _get(path: str) -> object:
    # Single retry on failure (rule #5: timeout + controlled retry, not infinite).
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = httpx.get(f"{BASE_URL}{path}", timeout=TIMEOUT)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
    raise GiosApiError(f"GET {path} failed after retry: {last_error}") from last_error


def fetch_all_stations() -> list[dict]:
    """GET /station/findAll — list of all measuring stations."""
    return _get("/station/findAll")  # type: ignore[return-value]


def fetch_sensors(station_id: str) -> list[dict]:
    """GET /station/sensors/{stationId} — sensors (parameters) at one station."""
    return _get(f"/station/sensors/{station_id}")  # type: ignore[return-value]


def fetch_sensor_data(sensor_id: str) -> dict:
    """GET /data/getData/{sensorId} — time series of values for one sensor."""
    return _get(f"/data/getData/{sensor_id}")  # type: ignore[return-value]
