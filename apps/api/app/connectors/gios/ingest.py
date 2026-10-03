"""Orchestrates one GIOŚ ingest run: fetch -> parse -> validate -> normalize -> store.

Deliberately manual/on-demand for this vertical slice (Phase 4) — the real scheduler
(who runs this, how often) is Phase 5 work per the roadmap, and per ADR-004 we don't
guess a polling frequency before it's verified. Run it yourself for now:

    docker compose exec api python -m app.connectors.gios.ingest --list
    docker compose exec api python -m app.connectors.gios.ingest --station-id 114
"""

import argparse
import logging
import os
import sys
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError

from app import provenance
from app.config import settings
from app.connectors.gios import client
from app.connectors.gios.parser import (
    PARAM_UNITS,
    PARSER_VERSION,
    GiosParseError,
    find_sensor,
    normalize,
    parse_values,
)
from app.connectors.gios.provider_index import ingest_index
from app.db import SessionLocal
from app.models import Measurement
from app.source_status import SMALL_SET_MAX_FAILED_FRACTION, record_source_run, run_failure_reason

logger = logging.getLogger(__name__)

MONITORED_PARAMS = list(PARAM_UNITS)


def gios_station_ids() -> list[str]:
    # ADR-007: which stations to poll is a deliberate, explicit choice (rule #9),
    # never guessed - comma-separated env var, empty means "skip GIOS". One parser
    # shared by the scheduler, the CLI and the health view so they cannot disagree.
    raw = os.environ.get("GIOS_STATION_IDS", "")
    return [s.strip() for s in raw.split(",") if s.strip()]


def run_failure(
    wanted: set[str], stations: list[dict], failed: int, errors: list[str] | None = None
) -> str | None:
    """Failure reason for one GIOS run (shared by scheduler and CLI), or None. The
    denominator is the CONFIGURED set: a requested id missing from the catalog counts
    as a failed station, so a mistyped/removed majority cannot hide behind the one
    station that still works."""
    matched = {str(s.get("Identyfikator stacji")) for s in stations}
    unmatched = wanted - matched
    if unmatched and errors is not None:
        errors.append(f"station id(s) not in catalog: {', '.join(sorted(unmatched))}")
    reason = run_failure_reason(
        len(wanted), failed + len(unmatched), max_failed_fraction=SMALL_SET_MAX_FAILED_FRACTION
    )
    return f"GIOS: {reason}" if reason else None


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
        size = settings.gios_data_size
        data = client.fetch_sensor_data(sensor_id, size=size)
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
        endpoint=f"{client.BASE_URL}{client.sensor_data_path(sensor_id, size)}",
        payload=data,
        fetched_at=fetched_at,
        parser_version=PARSER_VERSION,
    )
    try:
        parsed = parse_values(data)
        readings = parsed.readings
        skipped = len(parsed.rejected)
        # The CURRENT reading must be usable (a failed run, as before): if the newest entry that
        # carries a value is one we could not use, the window is not trustworthy. Older entries we
        # cannot use are skipped and counted.
        if parsed.rejected and not readings:
            raise GiosParseError(f"no usable value in the payload ({parsed.rejected[0][1]})")
        dated = [(naive, why) for naive, why in parsed.rejected if naive is not None]
        if readings and dated:
            naive, why = max(dated, key=lambda r: r[0])
            if naive > readings[-1][0].replace(tzinfo=None):
                raise GiosParseError(f"newest reading unusable ({why})")
        records: list[dict] = []
        for index, (observed_at, value) in enumerate(readings):
            try:
                records.append(
                    normalize(
                        station=station,
                        sensor=sensor,
                        observed_at=observed_at,
                        value=value,
                        fetched_at=fetched_at,
                    )
                )
            except GiosParseError as exc:
                if index == len(readings) - 1:
                    raise  # the CURRENT reading must be valid: a failed run, as before
                # an older value we cannot use must not hold back the rest of the window
                skipped += 1
                logger.warning(
                    "station %s (%s): skipping an older invalid value (%s)",
                    station_id,
                    formula,
                    exc,
                )
        # ADR-014: VALID = every record validated; PARTIAL = some were rejected (never silent)
        status = provenance.PARTIAL if skipped else provenance.VALID
    except (GiosParseError, KeyError) as exc:
        logger.warning(
            "station %s (%s): FAILED (%s), skipping — see rule #1", station_id, formula, exc
        )
        if errors is not None:
            errors.append(f"{type(exc).__name__}: {exc}")
        records, status = [], provenance.INVALID
    provenance.set_validation_status(db, fetch_id, status)
    if status == provenance.INVALID:
        return FAILED
    if not records:
        logger.info("station %s: no recent %s values, skipping", station_id, formula)
        return NOTHING_NEW

    # One response carries the whole window (hourly, newest first): every value we do not have yet
    # is stored, which also fills the hours a missed run left behind (rule #8: nothing is made up,
    # the source simply still lists them). A race with another run is retried once.
    stored = 0
    for _attempt in range(2):
        known = {
            row[0]
            for row in db.query(Measurement.source_record_id).filter(
                Measurement.source_id == "gios",
                Measurement.source_record_id.in_([r["source_record_id"] for r in records]),
            )
        }
        new = [r for r in records if r["source_record_id"] not in known]
        if not new:
            logger.info("station %s: %s readings already stored, skipping", station_id, formula)
            return NOTHING_NEW
        # ADR-014: every row points at the fetch that delivered it (one fetch -> many readings)
        db.add_all(Measurement(**r, source_fetch_id=fetch_id) for r in new)
        try:
            db.commit()
            stored = len(new)
            break
        except IntegrityError:
            db.rollback()  # another run stored some of them meanwhile: look again
    if not stored:
        return NOTHING_NEW
    newest = new[-1]
    logger.info(
        "station %s (%s): %s = %s %s (+%d new, newest %s)",
        station_id,
        newest["station_name"],
        formula,
        newest["value"],
        newest["unit"],
        stored,
        newest["observed_at"].isoformat(),
    )
    return STORED


def ingest_station(station: dict, db, errors: list[str] | None = None) -> int | None:
    """Returns the number of new readings stored across MONITORED_PARAMS, or None
    when the station yielded nothing but failures: fetch_sensors() failed, it has no
    monitored sensor, or every param that has a sensor failed (distinct from 0 =
    nothing new; the scheduler uses it to avoid recording an outage as success,
    TASK-13.1). Failure causes are appended to `errors` when given. One station's own
    failure is logged and skipped entirely — it must not abort ingestion for the rest
    of the run (rule #1); a single param's failure within a station is isolated by
    _ingest_param instead."""
    station_id = station.get("Identyfikator stacji")
    if settings.gios_provider_index_enabled:
        ingest_index(str(station_id), db)
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
    # No monitored sensor at all (catalog/schema change) is as useless as all failing.
    if not attempted:
        if errors is not None:
            errors.append(f"station {station_id}: no monitored sensors")
        return None
    if all(o == FAILED for o in attempted):
        return None
    return outcomes.count(STORED)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-off GIOŚ ingest (full MVP param set, TASK-4.1) — Master Plan §4."
    )
    parser.add_argument("--station-id", action="append", dest="station_ids", default=[])
    parser.add_argument("--list", action="store_true", help="preview one page of stations and exit")
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

    # ADR-012: a run over exactly the configured stations records source_status like
    # the scheduler; an ad-hoc subset says nothing about the source as a whole.
    record = wanted == set(gios_station_ids())
    db = SessionLocal()
    errors: list[str] = []
    try:
        try:
            matched = client.find_stations(wanted)  # catalog outage is a failed run too
            failed = sum(ingest_station(station, db, errors) is None for station in matched)
            failure = run_failure(wanted, matched, failed, errors)
            if failure:
                raise RuntimeError(failure)
        except Exception as exc:
            db.rollback()
            if record:
                cause = f"; last cause: {errors[-1]}" if errors else ""
                record_source_run(
                    db, "gios", success=False, error=f"{type(exc).__name__}: {exc}{cause}"
                )
            raise
        if record:
            record_source_run(db, "gios", success=True)
        else:
            logger.info("subset run (not GIOS_STATION_IDS): source_status not updated")
    finally:
        db.close()


if __name__ == "__main__":
    main()
