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


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)  # SQLite returns naive datetimes


def _store_batch(records: list[dict], db: Session, *, retry: bool = True) -> int:
    """All-or-nothing upsert of one geo_area's hourly rows in a single commit, so
    /pollen/latest never sees half of a forecast run. Keyed by source_record_id, whose
    forecast_reference_time is bucketed to the UTC day: a second fetch the same day (e.g.
    after the morning CAMS update, ADR-020) REPLACES the values, fetched_at and
    source_fetch_id of the overlapping hours instead of keeping the older run's numbers
    (ADR-014: a refreshed row points at the payload that produced it). Returns the
    number of rows inserted (not updated)."""
    # The whole bucket (one geo_area + one forecast_reference_time) is replaced: hours the
    # earlier same-day payload had but this one omits are deleted, otherwise superseded
    # future values would be served as part of the "newer" run.
    area_id, reference = records[0]["geo_area_id"], records[0]["forecast_reference_time"]
    existing = {
        row.source_record_id: row
        for row in db.execute(
            select(PollenSnapshot)
            .where(
                PollenSnapshot.source_id == SOURCE_ID,
                PollenSnapshot.geo_area_id == area_id,
                PollenSnapshot.forecast_reference_time == reference,
            )
            # Row locks (no-op on SQLite): a concurrent older run blocks here until the
            # newer one commits, then re-reads it and the fetched_at guard below holds.
            # A first-ever insert race is settled by the unique constraint instead.
            .with_for_update()
        ).scalars()
    }
    incoming_fetched_at = records[0]["fetched_at"]
    if any(_utc(row.fetched_at) > incoming_fetched_at for row in existing.values()):
        db.rollback()  # release the row locks
        return 0  # a concurrent run (scheduler + CLI) already stored a NEWER fetch - keep it
    inserted = 0
    incoming = set()
    for r in records:
        incoming.add(r["source_record_id"])
        row = existing.get(r["source_record_id"])
        if row is None:
            db.add(PollenSnapshot(**r))
            inserted += 1
        else:
            for column, value in r.items():
                setattr(row, column, value)
    for record_id, row in existing.items():
        if record_id not in incoming:
            db.delete(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # first-insert race with another run (nothing was there to lock)
        # One retry: now the other run's rows exist, so the lock + fetched_at guard decide
        # which payload wins (the older one is dropped, the newer one replaces).
        return _store_batch(records, db, retry=False) if retry else 0
    return inserted


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
        # Same area selection as the weather CLI/scheduler (ADR-019): never the whole
        # imported gmina list.
        areas = open_meteo_ingest.polling_areas(db, args.slugs)
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
