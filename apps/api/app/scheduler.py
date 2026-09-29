"""Minimal loop-based scheduler (ADR-007) — no job table, no queue, no separate
worker process: re-runs the existing connector ingest functions on a fixed
interval, in one process. Swap for a real queue/worker only when a second
replica actually needs to coordinate (see ADR-007 Consequences).

    docker compose up scheduler
"""

import logging
import os
import time

from app.connectors.gios import client as gios_client
from app.connectors.gios.ingest import ingest_station
from app.connectors.open_meteo.ingest import ingest_geo_area
from app.db import SessionLocal
from app.models import GeoArea

logger = logging.getLogger(__name__)

# ADR-004 verified cycles: Open-Meteo/ICON refreshes every 3h, GIOŚ measurement
# data is hourly.
OPEN_METEO_INTERVAL_SECONDS = 3 * 60 * 60
GIOS_INTERVAL_SECONDS = 60 * 60
POLL_INTERVAL_SECONDS = 60


def _gios_station_ids() -> list[str]:
    # ADR-007: which stations to poll is a deliberate, explicit choice (rule #9),
    # never guessed here - comma-separated env var, empty means "skip GIOS".
    raw = os.environ.get("GIOS_STATION_IDS", "")
    return [s.strip() for s in raw.split(",") if s.strip()]


def run_open_meteo() -> None:
    db = SessionLocal()
    try:
        for area in db.query(GeoArea).all():
            ingest_geo_area(area, db)
    finally:
        db.close()


def run_gios() -> None:
    station_ids = _gios_station_ids()
    if not station_ids:
        logger.info("GIOS_STATION_IDS not set - skipping scheduled GIOS ingest")
        return
    db = SessionLocal()
    try:
        for station in gios_client.find_stations(set(station_ids)):
            ingest_station(station, db)
    finally:
        db.close()


def main(*, iterations: int | None = None) -> None:
    """iterations caps the loop for tests; None (default) runs forever."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    last_open_meteo = last_gios = 0.0
    count = 0
    while iterations is None or count < iterations:
        now = time.monotonic()
        if now - last_open_meteo >= OPEN_METEO_INTERVAL_SECONDS:
            run_open_meteo()
            last_open_meteo = now
        if now - last_gios >= GIOS_INTERVAL_SECONDS:
            run_gios()
            last_gios = now
        count += 1
        if iterations is None or count < iterations:
            time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
