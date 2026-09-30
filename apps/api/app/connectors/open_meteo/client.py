"""HTTP client for the Open-Meteo forecast API (current weather).

Per docs/data/source-registry.md: shape is per official documentation
(open-meteo.com/en/docs) but NOT confirmed against a live sample in this
sandbox (api.open-meteo.com is robots.txt-blocked for this session's fetch
tools, and direct network from the shell is proxy-blocked to non-allowlisted
hosts). parser.py validates the shape and fails loudly rather than guessing.
Weather isn't safety-critical data (rule #10 is about alerts/water/air safety),
so docs-only verification is an accepted precedent here, unlike IMGW alerts.

Rate limit (600/min, source registry) is far above our need (a handful of
geo_areas every 3h per ADR-004) — no throttling required, unlike GIOŚ.
"""

from collections.abc import Callable

import httpx

BASE_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = httpx.Timeout(10.0, connect=5.0)

# Fields for "current conditions" — matches WeatherSnapshot.param_code values.
# Master Plan §5 MVP scope.
CURRENT_PARAMS = (
    "temperature_2m,relative_humidity_2m,apparent_temperature,pressure_msl,"
    "cloud_cover,precipitation,rain,snowfall,wind_speed_10m,wind_direction_10m,"
    "wind_gusts_10m,weather_code"
)

# Daily forecast fields (ADR-010, Master Plan §30). Deliberately narrow MVP set,
# not Open-Meteo's full daily catalog (YAGNI, same spirit as CURRENT_PARAMS).
DAILY_PARAMS = "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code"

# Last three §5 MVP fields (dew point, visibility, UV index): Open-Meteo's docs
# only list them under `hourly`, not `current` (TASK-5.4) - parser.py picks the
# entry matching current's hour out of this array instead of a second request.
HOURLY_PARAMS = "dew_point_2m,visibility,uv_index"


class OpenMeteoApiError(Exception):
    """Raised when Open-Meteo returns an unexpected status or unparseable body."""


def fetch_weather(
    latitude: float,
    longitude: float,
    *,
    on_attempt: Callable[[], None] | None = None,
) -> dict:
    """GET current weather + daily forecast for one point, in a single request
    (Open-Meteo supports combining `current` and `daily` in one call - ADR-010 -
    no need for a second HTTP round trip per geo_area). Single retry on failure
    (rule #5). Named `fetch_weather`, not `fetch_current`, because it now also
    carries the forecast block.

    `on_attempt` fires once per REAL outbound request, as a reservation made
    BEFORE that request goes out (not after it returns) — Codex review: firing it
    from `finally` after the request loses the record entirely if this process is
    killed while `httpx.get()` is in flight or after Open-Meteo has already
    processed (and billed) the request but before `finally` runs, defeating the
    counter's whole "survive a scheduler restart" point (rule #2). Reserving
    upfront can overcount by one call in the rare case this process dies between
    the reservation and the actual request going out — an acceptable direction to
    err on for a budget guard (Codex review [P1] on the units-per-call estimate:
    "never later" applies here too), unlike undercounting a request the provider
    already billed."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": CURRENT_PARAMS,
        "hourly": HOURLY_PARAMS,
        "daily": DAILY_PARAMS,
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
    raise OpenMeteoApiError(
        f"GET {BASE_URL} ({latitude}, {longitude}) failed after retry: {last_error}"
    ) from last_error
