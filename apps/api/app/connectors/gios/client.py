"""HTTP client for the GIOŚ (Główny Inspektorat Ochrony Środowiska) air quality API.

Verified against a LIVE response 2026-09-28 (see docs/data/source-registry.md). The
real payload is JSON-LD with Polish field names and paginated list endpoints — quite
different from the plain English-keyed shape this file originally (wrongly) assumed
before we had network access to test it. parser.py does the field-name mapping.
"""

import time
from collections.abc import Iterator

import httpx

BASE_URL = "https://api.gios.gov.pl/pjp-api/v1/rest"
TIMEOUT = httpx.Timeout(10.0, connect=5.0)

# station/findAll and station/sensors are list endpoints, rate-limited to 2 req/min
# per the Source Registry (rule #16: real verified limit, not a guess). The station
# list itself is documented as updating once a year (sy:updatePeriod: year) — walking
# every page is for on-demand discovery (Phase 4 CLI), never the scheduler hot path.
LIST_ENDPOINT_DELAY_SECONDS = 30
STATION_PAGE_SIZE = 100


class GiosApiError(Exception):
    """Raised when GIOŚ returns an unexpected status or unparseable body."""


def _get(path: str) -> dict:
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


def fetch_station_page(page: int = 0, size: int = 20) -> dict:
    """GET one page of /station/findAll, raw (with pagination metadata under
    'totalPages'/'links'). For CLI preview (--list) without paying the cost of
    walking every page."""
    return _get(f"/station/findAll?page={page}&size={size}")


def _iter_station_pages() -> Iterator[list[dict]]:
    """Walks every page of /station/findAll, sleeping between requests to respect
    the 2 req/min limit. Only for callers that actually need the full catalog."""
    page = 0
    while True:
        resp = fetch_station_page(page=page, size=STATION_PAGE_SIZE)
        yield resp["Lista stacji pomiarowych"]
        page += 1
        if page >= resp.get("totalPages", 1):
            return
        time.sleep(LIST_ENDPOINT_DELAY_SECONDS)


def fetch_all_stations() -> list[dict]:
    """GET all pages of /station/findAll, flattened. Slow on purpose (rate-limit
    delay between pages) — for one-off discovery, not the ingest hot path."""
    return [station for page in _iter_station_pages() for station in page]


def find_stations(station_ids: set[str]) -> list[dict]:
    """Walk station pages looking for specific IDs, stopping as soon as all are
    found. Ingesting one or two known stations shouldn't cost paging through the
    whole (rate-limited) catalog."""
    found: list[dict] = []
    found_ids: set[str] = set()
    for page in _iter_station_pages():
        for station in page:
            sid = str(station["Identyfikator stacji"])
            if sid in station_ids and sid not in found_ids:
                found.append(station)
                found_ids.add(sid)
        if found_ids >= station_ids:
            break
    return found


def fetch_sensors(station_id: str) -> list[dict]:
    """GET /station/sensors/{stationId}.
    ponytail: assumes one page is enough — real stations have a handful of sensors
    (verified: 5 for station 11), no pagination handling here. Add it if a station
    is ever seen with more than one page's worth."""
    resp = _get(f"/station/sensors/{station_id}")
    return resp["Lista stanowisk pomiarowych dla podanej stacji"]


def fetch_sensor_data(sensor_id: str) -> dict:
    """GET /data/getData/{sensorId} — time series of values for one sensor."""
    return _get(f"/data/getData/{sensor_id}")
