"""Orchestrates one IMGW hydro ingest run: fetch -> parse -> validate -> store.

One call returns every station (see client.py) - no per-station loop needed like
GIOŚ's two-step fetch. Manual/on-demand via this CLI, or scheduled (app/scheduler.py):

    docker compose exec api python -m app.connectors.imgw_hydro.ingest
"""

import logging
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError

from app.connectors.imgw_hydro import client
from app.connectors.imgw_hydro.parser import ImgwHydroParseError, normalize
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
        db.commit()
        return 1 if changed else 0

    db.add(Measurement(**record))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # race with another ingest run
        return 0
    return 1


def ingest_station(station: dict, db, *, fetched_at: datetime) -> int:
    """Returns the number of records actually stored/changed for this station
    (water level, plus warning/alarm thresholds when defined or changed). One
    station's bad record must not abort the run for the rest (rule #1)."""
    try:
        result = normalize(station, fetched_at=fetched_at)
    except ImgwHydroParseError as exc:
        sid = station.get("id_stacji")
        logger.warning("station %s: FAILED (%s), skipping - see rule #1", sid, exc)
        return 0
    if result is None:
        return 0  # no current reading for this station - not an error

    level = result["level"]
    stored = _insert_if_new(level, db)
    for threshold_record in result["thresholds"].values():
        stored += _upsert_or_delete_threshold(threshold_record, db)

    if stored:
        logger.info(
            "station %s (%s): stored/updated %s record(s), stan_wody = %s cm",
            level["station_id"],
            level["station_name"],
            stored,
            level["value"],
        )
    return stored


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    stations = client.fetch_stations()
    fetched_at = datetime.now(UTC)

    db = SessionLocal()
    try:
        stored = sum(ingest_station(s, db, fetched_at=fetched_at) for s in stations)
    finally:
        db.close()
    logger.info("imgw_hydro: stored %s/%s new readings", stored, len(stations))


if __name__ == "__main__":
    main()
