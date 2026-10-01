"""Raw ingestion / provenance (ADR-014, Master Plan §33-34): store what a source
returned next to the normalized rows, and purge old payloads.

Best-effort by design: a failed provenance write is logged and returns None; the
normalized rows are still stored with source_fetch_id NULL (rule #1 - an audit-table
hiccup must not cost users a flood alert or a PM2.5 reading).
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import CursorResult, null, update
from sqlalchemy.orm import Session

from app.models import SourceFetch

logger = logging.getLogger(__name__)

PENDING = "pending"  # recorded, parsing not finished (or the process died mid-parse)
VALID = "valid"  # every record parsed and validated
PARTIAL = "partial"  # some records/blocks rejected
INVALID = "invalid"  # payload unusable (unknown shape) - the case raw payloads exist for

# Master Plan §33: 7-30 days depending on source nature, cost and audit need.
# A source not listed here gets DEFAULT_RETENTION_DAYS (the shortest window), so a
# new connector must opt into a longer one explicitly (ADR-014).
RETENTION_DAYS = {
    "open_meteo": 7,  # not safety data, ~10 KB/fetch, re-fetchable forecast
    "imgw_hydro": 7,  # all-stations payload, hundreds of KB per hourly fetch
    "gios": 14,  # air quality, small payloads
    "imgw_warningshydro": 30,  # safety data (rule #10): longest audit window
}
DEFAULT_RETENTION_DAYS = 7


def record_fetch(
    db: Session,
    *,
    source_id: str,
    endpoint: str,
    payload: Any,
    fetched_at: datetime,
    parser_version: str,
    validation_status: str = PENDING,
) -> int | None:
    """Stores one raw fetch, returns its id, or None if the write failed."""
    try:
        row = SourceFetch(
            source_id=source_id,
            endpoint=endpoint,
            payload=payload,
            fetched_at=fetched_at,
            parser_version=parser_version,
            validation_status=validation_status,
        )
        db.add(row)
        db.flush()
        fetch_id = row.id
        db.commit()
        return fetch_id
    except Exception:
        db.rollback()
        logger.exception("could not record source_fetch for %s (%s)", source_id, endpoint)
        return None


def set_validation_status(db: Session, fetch_id: int | None, status: str) -> None:
    """Second phase for batch connectors, where the outcome is only known after every
    record was parsed. No-op for None (the provenance write had failed)."""
    if fetch_id is None:
        return
    try:
        db.execute(
            update(SourceFetch).where(SourceFetch.id == fetch_id).values(validation_status=status)
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("could not update validation_status of source_fetch %s", fetch_id)


def batch_status(total: int, rejected: int) -> str:
    if rejected == 0:
        return VALID
    return INVALID if rejected >= total else PARTIAL


def purge_expired_payloads(db: Session, *, now: datetime | None = None) -> int:
    """NULLs payloads older than each source's retention window; keeps the
    provenance metadata rows (ADR-014). Returns the number of payloads purged."""
    now = now or datetime.now(UTC)
    purged = 0
    for source_id, days in RETENTION_DAYS.items():
        purged += _purge(db, SourceFetch.source_id == source_id, now - timedelta(days=days))
    purged += _purge(
        db,
        SourceFetch.source_id.not_in(list(RETENTION_DAYS)),
        now - timedelta(days=DEFAULT_RETENTION_DAYS),
    )
    return purged


def _purge(db: Session, source_filter, cutoff: datetime) -> int:
    result = db.execute(
        update(SourceFetch)
        .where(source_filter, SourceFetch.payload.is_not(None), SourceFetch.fetched_at < cutoff)
        .values(payload=null())
    )
    db.commit()
    return cast(CursorResult, result).rowcount  # UPDATE always yields a CursorResult
