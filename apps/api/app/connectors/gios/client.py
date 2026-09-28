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


_last_list_call_at = 0.0


def _throttle_list_endpoint() -> None:
    """Enforce the 2 req/min spacing across EVERY list-type endpoint call
    (station/findAll page walks AND station/sensors) — not just consecutive page
    walks. Codex review flagged that per-station fetch_sensors() calls during
    multi-station ingest weren't covered by the old per-page-only delay, which
    could exhaust the limit and silently skip stations.

    ponytail: this timestamp is per-process only — two separate CLI invocations
    (e.g. `--list` then `--station-id` moments later) don't see each other's
    throttle state, so back-to-back manual runs can still exceed 2/min (flagged
    by Codex on PR #3). Not fixed here: the real scheduler (Phase 5) runs as one
    coordinated worker process, which is the right place for cross-invocation
    rate-limit state (e.g. via Redis), not this on-demand Phase 4 CLI."""
    global _last_list_call_at
    wait = LIST_ENDPOINT_DELAY_SECONDS - (time.monotonic() - _last_list_call_at)
    if wait > 0:
        time.sleep(wait)
    _last_list_call_at = time.monotonic()


def _get(path: str, *, throttle: bool = False) -> dict:
    # Single retry on failure (rule #5: timeout + controlled retry, not infinite).
    # `throttle` re-checks the list-endpoint spacing before EACH attempt (including
    # the retry) — Codex review found the retry itself could exceed 2/min otherwise.
    last_error: Exception | None = None
    for _attempt in range(2):
        if throttle:
            _throttle_list_endpoint()
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
    return _get(f"/station/findAll?page={page}&size={size}", throttle=True)


def _iter_station_pages() -> Iterator[list[dict]]:
    """Walks every page of /station/findAll (rate-limited via fetch_station_page).
    Only for callers that actually need the full catalog."""
    page = 0
    while True:
        resp = fetch_station_page(page=page, size=STATION_PAGE_SIZE)
        try:
            stations = resp["Lista stacji pomiarowych"]
        except KeyError as exc:
            # A shape we don't recognize must fail loudly as our own error type,
            # not a raw KeyError that ingest_station() doesn't know to catch
            # (rule #1: isolate failures, don't crash the whole ingest run).
            raise GiosApiError(f"unexpected findAll response shape: missing {exc}") from exc
        yield stations
        page += 1
        if page >= resp.get("totalPages", 1):
            return


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
    """GET /station/sensors/{stationId} — also a 2 req/min list endpoint, throttled
    the same as station/findAll (see _throttle_list_endpoint).
    ponytail: assumes one page is enough — real stations have a handful of sensors
    (verified: 5 for station 11), no pagination handling here. Add it if a station
    is ever seen with more than one page's worth."""
    resp = _get(f"/station/sensors/{station_id}", throttle=True)
    try:
        return resp["Lista stanowisk pomiarowych dla podanej stacji"]
    except KeyError as exc:
        raise GiosApiError(f"unexpected sensors response shape: missing {exc}") from exc


def fetch_sensor_data(sensor_id: str) -> dict:
    """GET /data/getData/{sensorId} — time series of values for one sensor."""
    return _get(f"/data/getData/{sensor_id}")
