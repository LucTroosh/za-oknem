"""HTTP client for IMGW-PIB's public meteorological warnings API.

Endpoint verified live 2026-09-29: one call returns either a list of active
warnings, or the confirmed-live "no active warnings" shape {"message": "Brak
ostrzeżeń meteorologicznych"}. parser.py handles both (same pattern as the
sibling imgw_warningshydro connector, ADR-009).
"""

import httpx

URL = "https://danepubliczne.imgw.pl/api/data/warningsmeteo"
TIMEOUT = httpx.Timeout(10.0, connect=5.0)


class ImgwWarningsMeteoApiError(Exception):
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
    raise ImgwWarningsMeteoApiError(f"GET {URL} failed after retry: {last_error}") from last_error
