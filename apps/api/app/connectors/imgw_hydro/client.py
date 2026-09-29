"""HTTP client for IMGW-PIB's public hydro API.

Endpoint + shape verified live 2026-09-29 (see docs/data/source-registry.md and
ADR-008): one call returns EVERY station, lat/lon included, no pagination and no
documented rate limit (unlike GIOŚ) - simpler than the GIOŚ client on purpose,
not an oversight.
"""

import httpx

URL = "https://danepubliczne.imgw.pl/api/data/hydro/"
TIMEOUT = httpx.Timeout(10.0, connect=5.0)


class ImgwHydroApiError(Exception):
    """Raised when IMGW returns an unexpected status or unparseable body."""


def fetch_stations() -> list[dict]:
    """GET all hydro stations in one call. Single retry on failure (rule #5)."""
    last_error: Exception | None = None
    for _attempt in range(2):
        try:
            response = httpx.get(URL, timeout=TIMEOUT)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list):
                raise ImgwHydroApiError(f"expected a list, got {type(data)!r}")
            return data
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
    raise ImgwHydroApiError(f"GET {URL} failed after retry: {last_error}") from last_error
