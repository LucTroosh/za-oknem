"""Orchestrates one IMGW hydro-warnings ingest run: fetch -> parse -> validate ->
store -> reconcile. One call returns every active warning - no per-station loop.

    docker compose exec api python -m app.connectors.imgw_warningshydro.ingest
"""

import logging
import sys
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError

from app.connectors.imgw_warningshydro import client
from app.connectors.imgw_warningshydro.parser import (
    ImgwWarningsHydroParseError,
    normalize,
    parse_warnings,
)
from app.db import SessionLocal
from app.models import Alert
from app.source_status import record_source_run

logger = logging.getLogger(__name__)


def _normalize_or_skip(warning: dict, *, fetched_at: datetime) -> dict | None:
    """None means the record was malformed and was logged/skipped (rule #1) -
    never raises, so one bad warning can't abort a batch. `warning` is typed as
    dict (the documented shape) but a live feed can send anything, so this
    still guards the log line against a non-dict entry at runtime."""
    try:
        return normalize(warning, fetched_at=fetched_at)
    except ImgwWarningsHydroParseError as exc:
        numer = warning.get("numer") if isinstance(warning, dict) else repr(warning)[:50]
        logger.warning("warning %s: FAILED (%s), skipping - see rule #1", numer, exc)
        return None


def _store(record: dict, db) -> bool:
    """Upserts by (source_id, source_record_id). Returns True only for a brand
    new alert (used for the "stored X new" log line/count) - an existing row is
    refreshed in place instead of left untouched, otherwise a warning that
    reappears after being closed out by _expire_withdrawn() would stay hidden
    forever under its stale valid_until (Codex review, PR #37)."""
    existing = (
        db.query(Alert)
        .filter_by(source_id=record["source_id"], source_record_id=record["source_record_id"])
        .first()
    )
    if existing:
        for field, value in record.items():
            setattr(existing, field, value)
        db.commit()
        return False

    db.add(Alert(**record))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # race with another ingest run - fine, alert exists now
        return False
    logger.info(
        "alert %s: %s (%s)",
        record["external_id"],
        record["event_type"],
        record["severity_raw"],
    )
    return True


def _expire_withdrawn(db, *, active_record_ids: set[str], fetched_at: datetime) -> int:
    """Rule #10: a warning IMGW has withdrawn must stop being reported as active -
    some warnings (e.g. hydrological drought) carry `valid_until` as far out as
    year 9999, so without this a withdrawn alert would look valid indefinitely.
    Closes out every currently-active row this source didn't report in the
    latest snapshot by setting its valid_until to the fetch time."""
    query = (
        db.query(Alert)
        .filter(Alert.source_id == "imgw_warningshydro")
        .filter(Alert.valid_until >= fetched_at)
    )
    # active_record_ids empty means IMGW is reporting zero active warnings right
    # now - every currently-active row is then stale, and .in_(()) on an empty
    # set is a SQLAlchemy anti-pattern (always-false, plus a warning), so skip it.
    if active_record_ids:
        query = query.filter(~Alert.source_record_id.in_(active_record_ids))
    stale = query.all()
    for alert in stale:
        alert.valid_until = fetched_at
    if stale:
        db.commit()
    return len(stale)


def ingest_warning(warning: dict, db, *, fetched_at: datetime) -> bool:
    """Returns True if a new alert was stored. One bad record must not abort the
    run for the rest (rule #1). Used standalone by tests/callers that don't need
    withdrawal reconciliation - see ingest_batch() for the full run."""
    record = _normalize_or_skip(warning, fetched_at=fetched_at)
    if record is None:
        return False
    return _store(record, db)


def ingest_batch(warnings: list, db, *, fetched_at: datetime) -> tuple[int, int, int]:
    """Stores every valid new/changed alert and, only when the whole snapshot
    parsed cleanly, expires ones IMGW withdrew since the last successful fetch.
    Returns (stored, expired, rejected) - `rejected` > 0 means the snapshot was
    incomplete, so callers must not treat this run as a clean success (ADR-012).
    This is the entry point both the CLI and the scheduler should call - see
    ADR-009."""
    records = [r for w in warnings if (r := _normalize_or_skip(w, fetched_at=fetched_at))]
    stored = sum(_store(r, db) for r in records)

    if len(records) < len(warnings):
        # A partially-malformed snapshot can't be trusted to say who's gone -
        # a still-valid alert that merely failed to parse this round would look
        # withdrawn otherwise (Codex review, PR #37). Skip reconciliation and
        # try again next run; the untouched alert stays reported until then.
        logger.warning(
            "imgw_warningshydro: %s/%s warnings failed to parse - skipping "
            "withdrawal reconciliation this run (rule #10)",
            len(warnings) - len(records),
            len(warnings),
        )
        return stored, 0, len(warnings) - len(records)

    active_ids = {r["source_record_id"] for r in records}
    expired = _expire_withdrawn(db, active_record_ids=active_ids, fetched_at=fetched_at)
    return stored, expired, 0


def main() -> None:
    """Manual/CLI ingest. Records its outcome in source_status exactly like the
    scheduler does (ADR-012) - operators may run only this path (no scheduler),
    and /alerts must then still be able to report a confirmed empty snapshot
    instead of staying UNAVAILABLE forever (Codex review)."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    db = SessionLocal()
    try:
        try:
            warnings = parse_warnings(client.fetch_warnings())
            fetched_at = datetime.now(UTC)
            stored, expired, rejected = ingest_batch(warnings, db, fetched_at=fetched_at)
        except Exception as exc:
            db.rollback()
            record_source_run(
                db, "imgw_warningshydro", success=False, error=f"{type(exc).__name__}: {exc}"
            )
            raise
        if rejected:
            # Incomplete snapshot: same rule as the scheduler - not a success.
            record_source_run(
                db,
                "imgw_warningshydro",
                success=False,
                error=f"{rejected} warning(s) failed to parse - snapshot incomplete",
            )
        else:
            record_source_run(db, "imgw_warningshydro", success=True)
    finally:
        db.close()
    logger.info(
        "imgw_warningshydro: stored %s/%s new alerts, expired %s withdrawn, rejected %s",
        stored,
        len(warnings),
        expired,
        rejected,
    )
    if rejected:
        sys.exit(1)


if __name__ == "__main__":
    main()
