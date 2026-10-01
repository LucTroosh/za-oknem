"""Orchestrates one Open-Meteo pollen ingest run: fetch -> record raw -> parse ->
store, per geo_area (ADR-020). Scheduled once a day (ADR-004: CAMS Europe publishes
once a day); manual/CLI:

    docker compose exec api python -m app.connectors.open_meteo_pollen.ingest
    docker compose exec api python -m app.connectors.open_meteo_pollen.ingest --slug klodzko
"""

import argparse
import logging
import sys
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import provenance
from app.connectors.open_meteo import ingest as open_meteo_ingest
from app.connectors.open_meteo_pollen import client
from app.connectors.open_meteo_pollen.parser import (
    PARSER_VERSION,
    SOURCE_ID,
    OpenMeteoPollenParseError,
    normalize,
)
from app.db import SessionLocal
from app.models import GeoArea, PollenSnapshot
from app.rate_budget import check_daily_budget, record_fetch_call
from app.source_status import record_source_run

logger = logging.getLogger(__name__)

# Open-Meteo's free-tier limits are per account/IP across its APIs (ADR-003), so pollen
# calls are counted in the SAME daily counter as the weather connector ("open_meteo")
# and the 70% alert reflects the combined usage. A pollen request has 5 variables and
# 4 forecast days, so under the documented rule (>10 variables or >14 days = more than
# one call) it is 1 unit. The pricing page does not say the rule applies to the Air
# Quality API, so 1 is an assumption - documented in ADR-020.
BUDGET_COUNTER = "open_meteo"
UNITS_PER_CALL = 1


def _store_batch(records: list[dict], db: Session) -> int:
    """All-or-nothing insert of one geo_area's new hourly rows in a single commit, so
    /pollen/latest never sees half of a forecast run. Deduped by source_record_id."""
    ids = [r["source_record_id"] for r in records]
    existing = set(
        db.execute(
            select(PollenSnapshot.source_record_id).where(
                PollenSnapshot.source_id == SOURCE_ID, PollenSnapshot.source_record_id.in_(ids)
            )
        ).scalars()
    )
    new = [PollenSnapshot(**r) for r in records if r["source_record_id"] not in existing]
    if not new:
        return 0
    db.add_all(new)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # race with another run - the next cycle retries
        return 0
    return len(new)


def ingest_geo_area(area: GeoArea, db: Session) -> bool:
    """True when the source answered with a payload that parsed (even if every row was
    already stored); False on fetch or parse failure. One geo_area's failure is logged
    and skipped - it must not abort the others (rule #1)."""

    def _on_attempt() -> None:
        count = record_fetch_call(db, BUDGET_COUNTER, units=UNITS_PER_CALL)
        check_daily_budget(BUDGET_COUNTER, count, open_meteo_ingest.DAILY_CALL_LIMIT)

    try:
        payload = client.fetch_pollen(area.latitude, area.longitude, on_attempt=_on_attempt)
    except client.OpenMeteoPollenApiError as exc:
        logger.warning("geo_area %s: pollen FAILED (%s), skipping - see rule #1", area.slug, exc)
        return False

    fetched_at = datetime.now(UTC)
    # ADR-014: raw payload first (pending) so it survives a parser crash, then the status.
    fetch_id = provenance.record_fetch(
        db,
        source_id=SOURCE_ID,
        # Query params are fixed by client.py (tracked by PARSER_VERSION); the point is
        # a public geo_area centroid, not user data.
        endpoint=f"{client.BASE_URL}?latitude={area.latitude}&longitude={area.longitude}",
        payload=payload,
        fetched_at=fetched_at,
        parser_version=PARSER_VERSION,
    )
    try:
        records = normalize(geo_area_id=area.id, payload=payload, fetched_at=fetched_at)
    except OpenMeteoPollenParseError as exc:
        logger.warning("geo_area %s: pollen payload REJECTED (%s)", area.slug, exc)
        provenance.set_validation_status(db, fetch_id, provenance.INVALID)
        return False
    provenance.set_validation_status(db, fetch_id, provenance.VALID)
    for r in records:
        r["source_fetch_id"] = fetch_id

    stored = _store_batch(records, db)
    logger.info("geo_area %s (%s): stored %s new pollen row(s)", area.slug, area.name, stored)
    return True


def ingest_areas(areas: list[GeoArea], db: Session) -> bool | None:
    """Runs every area. Returns None when there was nothing to do (no geo_areas - not a
    success), True when at least one area succeeded. Raises on TOTAL failure so
    source_status does not record a success for a run that fetched nothing (ADR-012).
    Partial failure is only logged: per-area freshness shows which area is stale."""
    if not areas:
        return None
    results = [ingest_geo_area(area, db) for area in areas]
    if not any(results):
        raise RuntimeError(f"pollen ingest failed for all {len(areas)} geo_area(s)")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Open-Meteo pollen ingest (Phase 8).")
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
        # ADR-012: the CLI records its outcome like the scheduler does.
        try:
            ingest_areas(areas, db)
        except Exception as exc:
            db.rollback()
            record_source_run(db, SOURCE_ID, success=False, error=f"{type(exc).__name__}: {exc}")
            raise
        record_source_run(db, SOURCE_ID, success=True)
    finally:
        db.close()


if __name__ == "__main__":
    main()
