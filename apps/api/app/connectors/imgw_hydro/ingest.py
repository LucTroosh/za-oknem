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


def ingest_station(station: dict, db, *, fetched_at: datetime) -> int:
    """Returns the number of new records stored for this station (0-3: water
    level, plus warning/alarm thresholds when defined). One station's bad record
    must not abort the run for the rest (rule #1)."""
    try:
        records = normalize(station, fetched_at=fetched_at)
    except ImgwHydroParseError as exc:
        sid = station.get("id_stacji")
        logger.warning("station %s: FAILED (%s), skipping - see rule #1", sid, exc)
        return 0
    if records is None:
        return 0  # no current reading for this station - not an error

    stored = 0
    for record in records:
        exists = (
            db.query(Measurement)
            .filter_by(source_id=record["source_id"], source_record_id=record["source_record_id"])
            .first()
        )
        if exists:
            continue
        db.add(Measurement(**record))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()  # race with another ingest run - fine, reading exists now
            continue
        stored += 1

    if stored:
        logger.info(
            "station %s (%s): stored %s reading(s), stan_wody = %s cm",
            records[0]["station_id"],
            records[0]["station_name"],
            stored,
            records[0]["value"],
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
