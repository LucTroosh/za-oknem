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

from app import provenance
from app.connectors.open_meteo import client
from app.connectors.open_meteo.client import CURRENT_PARAMS, DAILY_PARAMS, HOURLY_PARAMS
from app.connectors.open_meteo.parser import (
    PARSER_VERSION,
    OpenMeteoParseError,
    normalize,
    normalize_forecast,
    normalize_hourly_current,
)
from app.db import SessionLocal
from app.models import Forecast, GeoArea, WeatherSnapshot
from app.rate_budget import check_daily_budget, record_fetch_call

logger = logging.getLogger(__name__)

# ADR-003: 10 000 requests/day on Open-Meteo's free non-commercial tier -
# "alert przy 70% dziennego limitu" (see app/rate_budget.py).
DAILY_CALL_LIMIT = 10_000

# ADR-003 (docs/architecture/ADR-003-weather-provider-licensing.md:28-30): our
# request covers more than 1 "API call" worth of variables per Open-Meteo's own
# billing rules. Per open-meteo.com/en/pricing (verified 2026-09-29): "Requests for
# data covering more than 10 weather variables ... are considered multiple API
# calls" - example given is 15 variables = 1.5 calls, i.e. variables/10. We round UP
# so the budget alert can only trigger EARLIER than the real quota, never later
# (Codex review [P1]: undercounting delays the 70% alert past actual exhaustion).
# TASK-5.4 (now merged, PR #50) added HOURLY_PARAMS to the same request - counted
# here too, per this comment's own earlier note, so the estimate doesn't silently
# undercount again the moment both PRs land.
_TOTAL_VARIABLES = (
    len(CURRENT_PARAMS.split(",")) + len(HOURLY_PARAMS.split(",")) + len(DAILY_PARAMS.split(","))
)
ESTIMATED_BILLABLE_UNITS_PER_CALL = max(1, -(-_TOTAL_VARIABLES // 10))  # ceil division


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


def ingest_geo_area(area: GeoArea, db) -> int | None:
    """Returns the number of new rows stored (current-weather snapshots +
    hourly-derived fields + forecast days), or None when the fetch itself failed
    (distinct from 0 = fetched, nothing new; the scheduler needs the difference to
    avoid recording a total outage as a successful run, TASK-13.1). One
    geo_area's fetch failure is logged and skipped — it must not abort ingestion
    for the rest (rule #1).
    All three parse steps are isolated from each other too (ADR-010, TASK-5.4):
    a malformed block in one must not cost an otherwise-valid reading in another."""

    # ADR-001/ADR-003/ADR-004: count every REAL outbound request against the daily
    # budget and alert at 70% - via on_attempt, fired once per actual HTTP attempt
    # inside fetch_weather()'s own retry loop, not once per ingest_geo_area() call
    # (Codex review [P2]: a failed-then-retried-successfully fetch is 2 real
    # requests but was recorded as 1; two failed attempts were recorded as 0).
    # Each attempt bills ESTIMATED_BILLABLE_UNITS_PER_CALL, not 1 (Codex review [P1]
    # - see that constant's comment).
    def _on_attempt() -> None:
        count = record_fetch_call(db, "open_meteo", units=ESTIMATED_BILLABLE_UNITS_PER_CALL)
        check_daily_budget("open_meteo", count, DAILY_CALL_LIMIT)

    try:
        payload = client.fetch_weather(area.latitude, area.longitude, on_attempt=_on_attempt)
    except client.OpenMeteoApiError as exc:
        logger.warning("geo_area %s: FAILED (%s), skipping — see rule #1", area.slug, exc)
        return None

    fetched_at = datetime.now(UTC)
    stored = 0

    # ADR-014: raw payload first (status pending) - it survives a parser crash or a
    # worker kill - then all three blocks are parsed (each isolated, ADR-010/
    # TASK-5.4) and the status set, BEFORE any row is stored so every row can point
    # at the fetch.
    fetch_id = provenance.record_fetch(
        db,
        source_id="open_meteo",
        # Query params (variable lists) are fixed by client.py - tracked by PARSER_VERSION.
        endpoint=f"{client.BASE_URL}?latitude={area.latitude}&longitude={area.longitude}",
        payload=payload,
        fetched_at=fetched_at,
        parser_version=PARSER_VERSION,
    )
    failed_blocks = 0
    try:
        snapshots = normalize(geo_area_id=area.id, payload=payload, fetched_at=fetched_at)
    except OpenMeteoParseError as exc:
        logger.warning("geo_area %s: current weather FAILED (%s)", area.slug, exc)
        snapshots = []
        failed_blocks += 1

    # TASK-5.4: dew point/visibility/UV, own try/except - a hiccup in this newer,
    # hourly-array-derived block must not cost the already-proven current fields
    # above (rule #1, same isolation as forecast below).
    try:
        hourly_snapshots = normalize_hourly_current(
            geo_area_id=area.id, payload=payload, fetched_at=fetched_at
        )
    except OpenMeteoParseError as exc:
        logger.warning("geo_area %s: hourly-derived fields FAILED (%s)", area.slug, exc)
        hourly_snapshots = []
        failed_blocks += 1

    try:
        forecasts = normalize_forecast(geo_area_id=area.id, payload=payload, fetched_at=fetched_at)
    except OpenMeteoParseError as exc:
        logger.warning("geo_area %s: forecast FAILED (%s)", area.slug, exc)
        forecasts = []
        failed_blocks += 1

    provenance.set_validation_status(db, fetch_id, provenance.batch_status(3, failed_blocks))
    for r in (*snapshots, *hourly_snapshots, *forecasts):
        r["source_fetch_id"] = fetch_id

    stored += sum(_store_if_new(WeatherSnapshot, r, db) for r in snapshots)
    stored += sum(_store_if_new(WeatherSnapshot, r, db) for r in hourly_snapshots)
    stored += _store_forecast_batch(forecasts, db)

    logger.info(
        "geo_area %s (%s): stored %s new row(s) (%s current + %s hourly + %s forecast)",
        area.slug,
        area.name,
        stored,
        len(snapshots),
        len(hourly_snapshots),
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
