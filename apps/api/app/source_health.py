"""Operator-facing source health (TASK-13.1): per source, freshness of the last
successful run (rule #8), last attempt/success/error from `source_status`
(ADR-012) and today's call-budget usage (`source_fetch_counters`, TASK-13.1a).
Reads only our own DB (rule #14); no new table (ADR-012/ADR-007 state is reused).

Thresholds are NOT defined here: each source reuses the freshness function of
its own domain, already sized off that source's cycle (ADR-004, source-registry),
so the health view and the data endpoints can never disagree about "stale"."""

import logging
import os
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.api.v1.air import freshness as air_freshness
from app.api.v1.alerts import freshness as alerts_freshness
from app.api.v1.hydro import freshness as hydro_freshness
from app.api.v1.weather import freshness as weather_freshness
from app.connectors.open_meteo.ingest import DAILY_CALL_LIMIT as OPEN_METEO_DAILY_LIMIT
from app.models import SourceFetchCounter, SourceStatus
from app.source_status import source_freshness

logger = logging.getLogger(__name__)

MAX_PUBLIC_ERROR_LENGTH = 200


@dataclass(frozen=True)
class SourceSpec:
    freshness: Callable[[datetime], str]
    daily_limit: int | None = None  # None = no documented daily cap (source-registry)
    # False = deliberately switched off (not a fault): no alarm, `monitored: false`.
    enabled: Callable[[], bool] = lambda: True


# Exactly the source_ids the scheduler records in source_status (ADR-012).
# - open_meteo: ICON refreshes every 3h (registry, verified) -> weather thresholds 4h/8h.
# - gios: hourly measurements (registry, verified) -> air thresholds 2h/6h.
# - imgw_hydro / imgw_warningshydro: cycle NOT documented by IMGW (registry); the
#   1h poll and 2h/6h thresholds are the documented working assumption (ADR-008/009),
#   warnings being safety-critical (rule #16 exception).
SOURCES: dict[str, SourceSpec] = {
    "open_meteo": SourceSpec(weather_freshness, OPEN_METEO_DAILY_LIMIT),
    # ADR-007: GIOS is polled only for explicitly configured stations (rule #9).
    "gios": SourceSpec(
        air_freshness, enabled=lambda: bool(os.environ.get("GIOS_STATION_IDS", "").strip(", "))
    ),
    "imgw_hydro": SourceSpec(hydro_freshness),
    "imgw_warningshydro": SourceSpec(alerts_freshness),
}

# Error text comes from exception messages (HTTP libs embed URLs, sometimes with
# credentials). Redact URL userinfo, query strings and anything key/token/secret/
# password/authorization-like, including `access_token=x`, `x_api_key: x`, JSON
# `"token": "x"`. Input is capped first so the scan stays linear-ish (no ReDoS).
_USERINFO = re.compile(r"//[^/@\s]+@")
_QUERY = re.compile(r"(?<=\S)\?\S+")
# Authorization values can be multi-part (Basic x, AWS4-HMAC-SHA256 Credential=..,
# Signature=..): redact everything after the field name to the end of the message.
_AUTH = re.compile(r"""(?i)[\w-]*authorization[\w-]*["']?\s*[=:].*""")
_SECRET = re.compile(
    r"""(?i)[\w-]*(?:key|token|secret|password|passwd|authorization)[\w-]*["']?"""
    r"""\s*[=:]?\s*(?:bearer\s+)?["']?[^\s"',;&)]+["']?"""
)
_MAX_SCAN = 1000


def sanitize_error(error: str | None) -> str | None:
    if not error:
        return None
    text = " ".join(error[:_MAX_SCAN].split())
    text = _AUTH.sub("[redacted]", _QUERY.sub("", _USERINFO.sub("//[redacted]@", text)))
    text = _SECRET.sub("[redacted]", text)
    return text[:MAX_PUBLIC_ERROR_LENGTH]


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:  # SQLite returns naive datetimes
        return value.replace(tzinfo=UTC)
    return value


def _iso(value: datetime | None) -> str | None:
    value = _aware(value)
    return value.isoformat() if value else None


def _budget(db: Session, source_id: str, limit: int | None, today: date) -> dict | None:
    if limit is None:
        return None
    row = db.query(SourceFetchCounter).filter_by(source_id=source_id, day=today).one_or_none()
    used = row.count if row else 0
    return {"used": used, "limit": limit, "used_pct": round(100 * used / limit, 1)}


def _source_health(db: Session, source_id: str, spec: SourceSpec, today: date) -> dict:
    fresh = source_freshness(db, source_id, spec.freshness)
    row = db.get(SourceStatus, source_id)
    return {
        "source_id": source_id,
        "freshness": fresh["freshness"],
        "last_attempt_at": _iso(row.last_attempt_at) if row else None,
        "last_success_at": fresh["last_success_at"],
        "last_error": sanitize_error(row.last_error) if row else None,
        "monitored": spec.enabled(),
        "daily_budget": _budget(db, source_id, spec.daily_limit, today),
    }


def collect_source_health(db: Session, source_ids: Iterable[str] | None = None) -> list[dict]:
    """One entry per source. Rule #1: a failure while evaluating one source
    yields UNAVAILABLE for that source only, never a failed report."""
    today = datetime.now(UTC).date()
    report: list[dict] = []
    for source_id in source_ids if source_ids is not None else SOURCES:
        try:
            report.append(_source_health(db, source_id, SOURCES[source_id], today))
        except Exception:
            logger.exception("source health evaluation failed for %s", source_id)
            try:
                db.rollback()
            except Exception:  # broken connection: still produce the fallback entry
                logger.exception("rollback failed during source health evaluation")
            report.append(
                {
                    "source_id": source_id,
                    "freshness": "UNAVAILABLE",
                    "last_attempt_at": None,
                    "last_success_at": None,
                    "last_error": "health evaluation failed",
                    "daily_budget": None,
                    "monitored": SOURCES[source_id].enabled(),
                }
            )
    return report


def log_health_transitions(report: list[dict], previous: dict[str, str]) -> dict[str, str]:
    """Log once per state change, not per tick: STALE -> WARNING, UNAVAILABLE ->
    ERROR, leaving either -> INFO. `previous` is the caller's state (scheduler
    keeps it in memory); the first observation of a source that is already bad is
    also logged once. Returns the new state."""
    current: dict[str, str] = {}
    for entry in report:
        if not entry.get("monitored", True):
            continue  # deliberately disabled source: no alarm (and no stale state kept)
        source_id, state = entry["source_id"], entry["freshness"]
        current[source_id] = state
        before = previous.get(source_id)
        if state == before:
            continue
        detail = f"last_success_at={entry['last_success_at']} last_error={entry['last_error']}"
        if state == "UNAVAILABLE":
            logger.error("source %s is UNAVAILABLE (was %s): %s", source_id, before, detail)
        elif state == "STALE":
            logger.warning("source %s is STALE (was %s): %s", source_id, before, detail)
        elif before in ("STALE", "UNAVAILABLE"):
            logger.info("source %s recovered: %s -> %s", source_id, before, state)
    return current
