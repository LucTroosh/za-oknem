"""Orchestrates one IMGW hydro ingest run: fetch -> parse -> validate -> store.

One call returns every station (see client.py) - no per-station loop needed like
GIOŚ's two-step fetch. Manual/on-demand via this CLI, or scheduled (app/scheduler.py):

    docker compose exec api python -m app.connectors.imgw_hydro.ingest
"""

import logging
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError

from app import provenance
from app.connectors.imgw_hydro import client
from app.connectors.imgw_hydro.parser import PARSER_VERSION, ImgwHydroParseError, normalize
from app.db import SessionLocal
from app.models import Measurement

logger = logging.getLogger(__name__)


def _insert_if_new(record: dict, db) -> int:
    """Append-only: a genuinely new water-level reading (new observed_at from
    the source) is a new row; re-seeing the same one is a no-op."""
    exists = (
        db.query(Measurement)
        .filter_by(source_id=record["source_id"], source_record_id=record["source_record_id"])
        .first()
    )
    if exists:
        return 0
    db.add(Measurement(**record))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # race with another ingest run - fine, reading exists now
        return 0
    return 1


def _upsert_or_delete_threshold(record: dict, db) -> int:
    """Thresholds have no source-given timestamp of their own (see parser.py) -
    each ingest run reconciles the ONE row per (station, param_code) to whatever
    IMGW currently reports. record["value"] is None when IMGW currently defines
    no threshold: any previously stored row is deleted rather than left as a
    stale "latest" value (rule #10 - a withdrawn/changed threshold must not keep
    influencing the computed status)."""
    existing = (
        db.query(Measurement)
        .filter_by(source_id="imgw_hydro", source_record_id=record["source_record_id"])
        .first()
    )
    if record["value"] is None:
        if existing:
            db.delete(existing)
            db.commit()
        return 0  # a removal isn't a "new reading stored"

    if existing:
        changed = existing.value != record["value"]
        existing.value = record["value"]
        existing.observed_at = record["observed_at"]
        existing.fetched_at = record["fetched_at"]
        existing.source_fetch_id = record.get("source_fetch_id")
        db.commit()
        return 1 if changed else 0

    db.add(Measurement(**record))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # race with another ingest run
        return 0
    return 1


def ingest_station(
    station: dict, db, *, fetched_at: datetime, source_fetch_id: int | None = None
) -> int:
    return _ingest_station(station, db, fetched_at=fetched_at, source_fetch_id=source_fetch_id) or 0


def _ingest_station(
    station: dict, db, *, fetched_at: datetime, source_fetch_id: int | None
) -> int | None:
    """Returns the number of records actually stored/changed for this station
    (water level, plus warning/alarm thresholds when defined or changed). One
    station's bad record must not abort the run for the rest (rule #1).
    `source_fetch_id` (ADR-014) links stored rows to the raw payload of this run.
    This inner variant returns None for a station that failed to parse (so the
    caller can count rejects); ingest_station() maps that to 0."""
    try:
        result = normalize(station, fetched_at=fetched_at)
    except ImgwHydroParseError as exc:
        sid = station.get("id_stacji")
        logger.warning("station %s: FAILED (%s), skipping - see rule #1", sid, exc)
        return None

    # Thresholds are reconciled even when the station has no current stan_wody
    # reading (level is None) - a stalled station can still have its threshold
    # change or get withdrawn, and that must not be silently skipped (rule #1
    # is about isolating a BROKEN station, not about dropping unrelated fields
    # just because one is legitimately absent - Codex review, PR #42 round 4).
    level = result["level"]
    if level is not None:
        level["source_fetch_id"] = source_fetch_id
    stored = _insert_if_new(level, db) if level is not None else 0
    for threshold_record in result["thresholds"].values():
        threshold_record["source_fetch_id"] = source_fetch_id
        stored += _upsert_or_delete_threshold(threshold_record, db)

    if stored:
        logger.info(
            "station %s (%s): stored/updated %s record(s)%s",
            result["station_id"],
            result["station_name"],
            stored,
            f", stan_wody = {level['value']} cm" if level is not None else "",
        )
    return stored


def ingest_snapshot(stations: list[dict], db, *, fetched_at: datetime) -> tuple[int, int]:
    """One whole IMGW response: records the raw payload (ADR-014), ingests every
    station, then sets the validation status. Returns (stored, rejected) - rejected
    counts stations whose record failed to parse. The scheduler and the CLI both
    call this, so they cannot diverge."""
    fetch_id = provenance.record_fetch(
        db,
        source_id="imgw_hydro",
        endpoint=client.URL,
        payload=stations,
        fetched_at=fetched_at,
        parser_version=PARSER_VERSION,
    )
    stored = 0
    rejected = 0
    for station in stations:
        count = _ingest_station(station, db, fetched_at=fetched_at, source_fetch_id=fetch_id)
        if count is None:
            rejected += 1
        else:
            stored += count
    provenance.set_validation_status(db, fetch_id, provenance.batch_status(len(stations), rejected))
    return stored, rejected


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    stations = client.fetch_stations()
    fetched_at = datetime.now(UTC)

    db = SessionLocal()
    try:
        stored, _rejected = ingest_snapshot(stations, db, fetched_at=fetched_at)
    finally:
        db.close()
    logger.info("imgw_hydro: stored %s/%s new readings", stored, len(stations))


if __name__ == "__main__":
    main()
