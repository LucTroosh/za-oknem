"""Orchestrates one GIOŚ ingest run: fetch -> parse -> validate -> normalize -> store.

Deliberately manual/on-demand for this vertical slice (Phase 4) — the real scheduler
(who runs this, how often) is Phase 5 work per the roadmap, and per ADR-004 we don't
guess a polling frequency before it's verified. Run it yourself for now:

    docker compose exec api python -m app.connectors.gios.ingest --list
    docker compose exec api python -m app.connectors.gios.ingest --station-id 114
"""

import argparse
import logging
import sys
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError

from app import provenance
from app.connectors.gios import client
from app.connectors.gios.parser import (
    PARAM_UNITS,
    PARSER_VERSION,
    GiosParseError,
    find_sensor,
    latest_value,
    normalize,
)
from app.db import SessionLocal
from app.models import Measurement
from app.source_status import record_source_run

logger = logging.getLogger(__name__)

MONITORED_PARAMS = list(PARAM_UNITS)

# _ingest_param outcomes. TASK-13.1: "failed" (fetch/parse error) must stay distinct
# from "nothing new" - otherwise a 429 on every param looks like a successful run.
STORED, NOTHING_NEW, NO_SENSOR, FAILED = "stored", "nothing_new", "no_sensor", "failed"


def _ingest_param(
    station: dict, sensors: list[dict], formula: str, db, errors: list[str] | None = None
) -> str:
    """One param for one station; returns STORED / NOTHING_NEW / NO_SENSOR / FAILED.
    Isolated per-param (not just per-station, rule #1) — a shape problem with e.g.
    CO must not skip PM2.5/PM10/etc. for the same station."""
    station_id = station.get("Identyfikator stacji")
    try:
        sensor = find_sensor(sensors, formula)
        if sensor is None:
            logger.info("station %s: no %s sensor, skipping", station_id, formula)
            return NO_SENSOR
        sensor_id = str(sensor["Identyfikator stanowiska"])
        data = client.fetch_sensor_data(sensor_id)
    except (client.GiosApiError, GiosParseError, KeyError) as exc:
        # KeyError: malformed sensor dict (e.g. missing "Identyfikator stanowiska")
        # must stay inside this param's isolation too (Codex review) — otherwise it
        # escapes _ingest_param uncaught and aborts every remaining param for this
        # station, contradicting the per-param isolation this function promises.
        logger.warning(
            "station %s (%s): FAILED (%s), skipping — see rule #1", station_id, formula, exc
        )
        if errors is not None:
            errors.append(f"{type(exc).__name__}: {exc}")
        return FAILED

    # ADR-014: the raw payload is stored BEFORE parsing (status pending), so it
    # survives a parser crash or a worker kill too - a changed API shape is exactly
    # the case it exists for. One fetch per sensor = one Measurement, so the link is
    # unambiguous. The station/sensor catalog calls are not stored: they only supply
    # metadata (name, coordinates), not the value.
    fetched_at = datetime.now(UTC)
    fetch_id = provenance.record_fetch(
        db,
        source_id="gios",
        endpoint=f"{client.BASE_URL}/data/getData/{sensor_id}",
        payload=data,
        fetched_at=fetched_at,
        parser_version=PARSER_VERSION,
    )
    try:
        result = latest_value(data)
        record: dict | None = None
        if result is not None:
            observed_at, value = result
            record = normalize(
                station=station,
                sensor=sensor,
                observed_at=observed_at,
                value=value,
                fetched_at=fetched_at,
            )
        status = provenance.VALID
    except (GiosParseError, KeyError) as exc:
        logger.warning(
            "station %s (%s): FAILED (%s), skipping — see rule #1", station_id, formula, exc
        )
        if errors is not None:
            errors.append(f"{type(exc).__name__}: {exc}")
        record, status = None, provenance.INVALID
    provenance.set_validation_status(db, fetch_id, status)
    if status == provenance.INVALID:
        return FAILED
    if record is None:
        logger.info("station %s: no recent %s values, skipping", station_id, formula)
        return NOTHING_NEW
    record["source_fetch_id"] = fetch_id

    exists = (
        db.query(Measurement)
        .filter_by(source_id=record["source_id"], source_record_id=record["source_record_id"])
        .first()
    )
    if exists:
        logger.info("station %s: %s reading already stored, skipping", station_id, formula)
        return NOTHING_NEW

    db.add(Measurement(**record))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # race with another ingest run — fine, reading exists now
        return NOTHING_NEW
    logger.info(
        "station %s (%s): %s = %s %s",
        station_id,
        record["station_name"],
        formula,
        record["value"],
        record["unit"],
    )
    return STORED


def ingest_station(station: dict, db, errors: list[str] | None = None) -> int | None:
    """Returns the number of new readings stored across MONITORED_PARAMS, or None
    when the station yielded nothing but failures: fetch_sensors() failed, or every
    param that has a sensor failed (distinct from 0 = nothing new; the scheduler uses
    it to avoid recording an outage as success, TASK-13.1). Failure causes are
    appended to `errors` when given. One station's own failure is logged and skipped
    entirely — it must not abort ingestion for the rest of the run (rule #1); a
    single param's failure within a station is isolated by _ingest_param instead."""
    station_id = station.get("Identyfikator stacji")
    try:
        sensors = client.fetch_sensors(str(station_id))
    except client.GiosApiError as exc:
        logger.warning("station %s: FAILED (%s), skipping — see rule #1", station_id, exc)
        if errors is not None:
            errors.append(f"{type(exc).__name__}: {exc}")
        return None

    outcomes = [
        _ingest_param(station, sensors, formula, db, errors) for formula in MONITORED_PARAMS
    ]
    attempted = [o for o in outcomes if o != NO_SENSOR]
    if attempted and all(o == FAILED for o in attempted):
        return None
    return outcomes.count(STORED)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-off GIOŚ ingest (full MVP param set, TASK-4.1) — Master Plan §4."
    )
    parser.add_argument("--station-id", action="append", dest="station_ids", default=[])
    parser.add_argument(
        "--list", action="store_true", help="preview one page of stations and exit"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.list:
        # One page only (fast, one request) — the full catalog is 15+ pages and
        # rate-limited to 2 req/min (see client.fetch_all_stations if you really
        # need the whole thing).
        page = client.fetch_station_page()
        for s in page["Lista stacji pomiarowych"]:
            print(f"{s['Identyfikator stacji']}: {s['Nazwa stacji']}")
        print(
            f"... page 1 of {page.get('totalPages')} total pages. Station list is "
            "rate-limited (2 req/min) — re-run with --station-id <id> once you have one."
        )
        return

    if not args.station_ids:
        print("No --station-id given. Run with --list first to pick one.", file=sys.stderr)
        sys.exit(1)

    wanted = {str(sid) for sid in args.station_ids}

    db = SessionLocal()
    errors: list[str] = []
    try:
        # ADR-012: the CLI records its outcome like the scheduler (same success rule).
        try:
            matched = client.find_stations(wanted)  # catalog outage is a failed run too
            failed = sum(ingest_station(station, db, errors) is None for station in matched)
            if not matched or failed == len(matched):
                raise RuntimeError(
                    f"GIOS: no data fetched ({len(matched)} station(s), {failed} failed)"
                )
        except Exception as exc:
            db.rollback()
            cause = f"; last cause: {errors[-1]}" if errors else ""
            record_source_run(
                db, "gios", success=False, error=f"{type(exc).__name__}: {exc}{cause}"
            )
            raise
        record_source_run(db, "gios", success=True)
    finally:
        db.close()


if __name__ == "__main__":
    main()
