"""HTTP client for the seven new GIOŚ datasets (ADR-032 pkt 8-9, GIOS-02).

Rules this encodes (docs/data/gios/02-development-contract.md, 06-verification.md):
- timeouts: connect 5 s, read 20 s (OUR budget, not a provider promise); at most
  `gios_open_max_retries` retries after the first attempt, only for timeouts / connection
  errors / 429 / 502 / 503 / 504, honouring `Retry-After` (capped) plus jitter. A validation
  error (HTTP 4xx, `wynik.status = BLAD`) is never retried (rule #5: bounded, controlled).
- every attempt, retries included, takes a slot from the per-service limiter;
- HTTP 200 does not mean success: `wynik.status = BLAD` is a source error;
- `SUKCES` with `liczbaRekordow = 0` and no `strona` is an OBSERVED empty result; a body that is
  not an envelope at all, or claims records without a `strona`, is a contract error;
- `liczbaRekordow` is reported but never treated as a total (in the live samples it equals the
  page size); `wynik.data` is never a measurement time (no offset, UTC by the spec only).
Nothing here knows about any particular dataset.
"""

import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings
from app.gios_open.errors import (
    GiosOpenContractError,
    GiosOpenSourceError,
    GiosOpenTransportError,
)

logger = logging.getLogger(__name__)

RETRY_STATUS = frozenset({429, 502, 503, 504})
MAX_RETRY_AFTER_SECONDS = 60.0
BACKOFF_BASE_SECONDS = 1.0
JITTER_SECONDS = 1.0


@dataclass(frozen=True)
class Page:
    """One parsed page. `records` may be empty (then `empty_observed` says the source itself
    reported an empty result). `reported_count` is `liczbaRekordow` as sent: NOT a total."""

    records: list[dict]
    reported_count: int | None
    empty_observed: bool
    event_id: str | None
    raw: dict


class MinIntervalLimiter:
    """At least `min_interval` seconds between two calls (one request per N seconds). Process-wide
    per service; clock and sleeper are injectable for tests."""

    def __init__(
        self,
        min_interval: float,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ):
        self.min_interval = min_interval
        self._clock = clock
        self._sleeper = sleeper
        self._last: float | None = None

    def wait(self) -> None:
        if self._last is not None:
            remaining = self.min_interval - (self._clock() - self._last)
            if remaining > 0:
                self._sleeper(remaining)
        self._last = self._clock()


_LIMITERS: dict[str, MinIntervalLimiter] = {}


def limiter_for(service: str) -> MinIntervalLimiter:
    """The shared limiter of a service (concurrency is 1 per service, ADR-032 pkt 8)."""
    if service not in _LIMITERS:
        _LIMITERS[service] = MinIntervalLimiter(settings.gios_open_min_interval_seconds)
    return _LIMITERS[service]


def _is_int(x: Any) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def parse_envelope(body: Any) -> Page:
    """Turns a decoded JSON body into a `Page`, or raises. See the module docstring."""
    if not isinstance(body, dict):
        raise GiosOpenContractError(f"body is {type(body).__name__}, expected an object")
    wynik = body.get("wynik")
    event_id: str | None = None
    if isinstance(wynik, dict):
        raw_id = wynik.get("idZdarzenia")
        event_id = raw_id if isinstance(raw_id, str) else None
        status = wynik.get("status")
        if status == "BLAD":
            err = wynik.get("blad")
            err = err if isinstance(err, dict) else {}
            code, desc = err.get("kod"), err.get("opis")
            raise GiosOpenSourceError(
                str(code) if code is not None else None,
                str(desc) if desc is not None else None,
                event_id,
            )
        if status != "SUKCES":
            raise GiosOpenContractError(f"unknown wynik.status {status!r}")
    elif "features" not in body:
        # The GeoJSON-style operations (noise ranges) carry `features` at the top level, may have
        # no `wynik`; anything else without it is not an envelope.
        raise GiosOpenContractError("no `wynik` envelope")

    if "features" in body:
        records, count = body.get("features"), body.get("liczbaRekordow")
    else:
        dane = body.get("dane")
        if not isinstance(dane, dict):
            raise GiosOpenContractError("SUKCES without `dane`")
        records, count = dane.get("strona"), dane.get("liczbaRekordow")
        if records is None:
            # Observed on a real empty answer: {"dane": {"liczbaRekordow": 0}, "wynik": SUKCES}.
            if count == 0 and _is_int(count):
                records = []
            else:
                raise GiosOpenContractError("`dane` without `strona` and without liczbaRekordow=0")
    if not isinstance(records, list) or not all(isinstance(r, dict) for r in records):
        raise GiosOpenContractError("records are not a list of objects")
    return Page(
        records=records,
        reported_count=count if _is_int(count) else None,
        empty_observed=len(records) == 0,
        event_id=event_id,
        raw=body,
    )


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After")
    if value is None:
        return None
    try:
        seconds = float(value)
    except ValueError:  # an HTTP-date form: not worth parsing, fall back to our backoff
        return None
    return min(max(seconds, 0.0), MAX_RETRY_AFTER_SECONDS)


class GiosOpenClient:
    def __init__(
        self,
        service: str,
        *,
        limiter: MinIntervalLimiter | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        rng: Callable[[], float] = random.random,
    ):
        self.service = service
        self.base_url = f"{settings.gios_open_base_url}/{service}"
        self.limiter = limiter if limiter is not None else limiter_for(service)
        self._sleep = sleeper
        self._rng = rng

    def url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def get_page(self, path: str, params: dict[str, Any] | None = None) -> Page:
        timeout = httpx.Timeout(
            settings.gios_open_read_timeout_seconds,
            connect=settings.gios_open_connect_timeout_seconds,
        )
        attempts = 1 + settings.gios_open_max_retries
        last: str = ""
        for attempt in range(attempts):
            self.limiter.wait()  # retries use the budget too
            delay: float | None = None
            try:
                response = httpx.get(self.url(path), params=params, timeout=timeout)
            except httpx.TransportError as exc:  # timeouts, connection errors
                last = f"{type(exc).__name__}: {exc}"
            else:
                code = response.status_code
                if code in RETRY_STATUS:
                    last = f"HTTP {code}"
                    delay = _retry_after(response)
                elif code >= 400:
                    raise GiosOpenTransportError(f"GET {self.url(path)} -> HTTP {code}")
                else:
                    try:
                        body = response.json()
                    except ValueError as exc:
                        raise GiosOpenContractError(f"body is not JSON: {exc}") from exc
                    return parse_envelope(body)  # BLAD raises here and is NOT retried
            if attempt + 1 < attempts:
                if delay is None:
                    delay = BACKOFF_BASE_SECONDS * (2**attempt)
                self._sleep(delay + self._rng() * JITTER_SECONDS)
        raise GiosOpenTransportError(
            f"GET {self.url(path)} failed after {attempts} attempts: {last}"
        )
