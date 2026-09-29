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


def ingest_station(station: dict, db, *, fetched_at: datetime) -> bool:
    """Returns True if a new reading was stored. One station's bad record must not
    abort the run for the rest (rule #1)."""
    try:
        record = normalize(station, fetched_at=fetched_at)
    except ImgwHydroParseError as exc:
        sid = station.get("id_stacji")
        logger.warning("station %s: FAILED (%s), skipping - see rule #1", sid, exc)
        return False
    if record is None:
        return False  # no current reading for this station - not an error

    exists = (
        db.query(Measurement)
        .filter_by(source_id=record["source_id"], source_record_id=record["source_record_id"])
        .first()
    )
    if exists:
        return False

    db.add(Measurement(**record))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # race with another ingest run - fine, reading exists now
        return False
    logger.info(
        "station %s (%s): stan_wody = %s cm",
        record["station_id"],
        record["station_name"],
        record["value"],
    )
    return True


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
