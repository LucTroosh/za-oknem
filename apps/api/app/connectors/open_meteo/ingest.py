"""Orchestrates one Open-Meteo ingest run: fetch -> parse -> validate -> store,
for every geo_area (or a --slug subset). Stores both current-weather snapshots
and forecast days from the same fetch (ADR-010).

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
from app.connectors.open_meteo.parser import OpenMeteoParseError, normalize, normalize_forecast
from app.db import SessionLocal
from app.models import Forecast, GeoArea, WeatherSnapshot

logger = logging.getLogger(__name__)


def _store_if_new(model_cls: type, record: dict, db) -> int:
    """Insert-if-new for WeatherSnapshot rows - each param commits on its own,
    deduped by (source_id, source_record_id)."""
    exists = (
        db.query(model_cls)
        .filter_by(source_id=record["source_id"], source_record_id=record["source_record_id"])
        .first()
    )
    if exists:
        return 0
    db.add(model_cls(**record))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # race with another ingest run — fine, row exists now
        return 0
    return 1


def _store_forecast_batch(records: list[dict], db) -> int:
    """Insert all-or-nothing for one geo_area's forecast rows, in a single commit
    - unlike _store_if_new's per-record commits, a forecast batch spans several
    days/params that /weather/forecast presents together (grouped by day), so a
    partial commit (interrupted run, mid-batch DB error) would let that endpoint
    silently mix one day's new reference_time with another's stale one."""
    new_records = []
    for r in records:
        exists = (
            db.query(Forecast)
            .filter_by(source_id=r["source_id"], source_record_id=r["source_record_id"])
            .first()
        )
        if not exists:
            new_records.append(Forecast(**r))
    if not new_records:
        return 0
    db.add_all(new_records)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # race with another ingest run — next scheduled cycle retries
        return 0
    return len(new_records)


def ingest_geo_area(area: GeoArea, db) -> int:
    """Returns the number of new rows stored (current-weather snapshots +
    forecast days). One geo_area's fetch failure is logged and skipped — it
    must not abort ingestion for the rest (rule #1). Current and forecast
    parsing are isolated from each other too (ADR-010): a malformed `daily`
    block must not cost us an otherwise-valid `current` reading, or vice versa."""
    try:
        payload = client.fetch_weather(area.latitude, area.longitude)
    except client.OpenMeteoApiError as exc:
        logger.warning("geo_area %s: FAILED (%s), skipping — see rule #1", area.slug, exc)
        return 0

    fetched_at = datetime.now(UTC)
    stored = 0

    try:
        snapshots = normalize(geo_area_id=area.id, payload=payload, fetched_at=fetched_at)
    except OpenMeteoParseError as exc:
        logger.warning("geo_area %s: current weather FAILED (%s)", area.slug, exc)
        snapshots = []
    stored += sum(_store_if_new(WeatherSnapshot, r, db) for r in snapshots)

    try:
        forecasts = normalize_forecast(geo_area_id=area.id, payload=payload, fetched_at=fetched_at)
    except OpenMeteoParseError as exc:
        logger.warning("geo_area %s: forecast FAILED (%s)", area.slug, exc)
        forecasts = []
    stored += _store_forecast_batch(forecasts, db)

    logger.info(
        "geo_area %s (%s): stored %s new row(s) (%s current + %s forecast)",
        area.slug,
        area.name,
        stored,
        len(snapshots),
        len(forecasts),
    )
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
