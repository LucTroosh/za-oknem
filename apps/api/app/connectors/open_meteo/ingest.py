"""Orchestrates one Open-Meteo ingest run: fetch -> parse -> validate -> store,
for every geo_area (or a --slug subset).

Manual/on-demand for now, same as GIOŚ (Phase 4/5) — the real scheduler is Phase 5
follow-up work; per ADR-004 fetch this every 3h once scheduled, not more often:

    docker compose exec api python -m app.connectors.open_meteo.ingest
    docker compose exec api python -m app.connectors.open_meteo.ingest --slug klodzko
"""

import argparse
import logging
import sys
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError

from app.connectors.open_meteo import client
from app.connectors.open_meteo.parser import OpenMeteoParseError, normalize
from app.db import SessionLocal
from app.models import GeoArea, WeatherSnapshot

logger = logging.getLogger(__name__)


def ingest_geo_area(area: GeoArea, db) -> int:
    """Returns the number of new snapshot rows stored. One geo_area's failure is
    logged and skipped — it must not abort ingestion for the rest (rule #1)."""
    try:
        payload = client.fetch_current(area.latitude, area.longitude)
        records = normalize(geo_area_id=area.id, payload=payload, fetched_at=datetime.now(UTC))
    except (client.OpenMeteoApiError, OpenMeteoParseError) as exc:
        logger.warning("geo_area %s: FAILED (%s), skipping — see rule #1", area.slug, exc)
        return 0

    stored = 0
    for record in records:
        exists = (
            db.query(WeatherSnapshot)
            .filter_by(source_id=record["source_id"], source_record_id=record["source_record_id"])
            .first()
        )
        if exists:
            continue
        db.add(WeatherSnapshot(**record))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()  # race with another ingest run — fine, row exists now
            continue
        stored += 1

    logger.info("geo_area %s (%s): stored %s/%s params", area.slug, area.name, stored, len(records))
    return stored


def main() -> None:
    parser = argparse.ArgumentParser(description="Open-Meteo current-weather ingest (Phase 5).")
    parser.add_argument("--slug", action="append", dest="slugs", default=[])
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    db = SessionLocal()
    try:
        query = db.query(GeoArea)
        if args.slugs:
            query = query.filter(GeoArea.slug.in_(args.slugs))
        areas = query.all()
        if not areas:
            print("No matching geo_areas found.", file=sys.stderr)
            sys.exit(1)
        for area in areas:
            ingest_geo_area(area, db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
