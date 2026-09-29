"""HTTP client for IMGW-PIB's public hydrological warnings API.

Endpoint verified live 2026-09-29 (ADR-009): one call returns either a list of
active warnings, or - the known "empty" shape for the sibling warningsmeteo
endpoint, not independently confirmed here - {"message": "..."}. parser.py
handles both defensively rather than guessing which one this endpoint uses.
"""

import httpx

URL = "https://danepubliczne.imgw.pl/api/data/warningshydro"
TIMEOUT = httpx.Timeout(10.0, connect=5.0)


class ImgwWarningsHydroApiError(Exception):
    """Raised when IMGW returns an unexpected status or unparseable body."""


def fetch_warnings() -> list | dict:
    """GET the raw payload (list or message-dict - see parser.py). Single retry
    on failure (rule #5)."""
    last_error: Exception | None = None
    for _attempt in range(2):
        try:
            response = httpx.get(URL, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
    raise ImgwWarningsHydroApiError(f"GET {URL} failed after retry: {last_error}") from last_error
