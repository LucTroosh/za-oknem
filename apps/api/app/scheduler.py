"""Minimal loop-based scheduler (ADR-007) — no job table, no queue, no separate
worker process: re-runs the existing connector ingest functions on a fixed
interval, in one process. Swap for a real queue/worker only when a second
replica actually needs to coordinate (see ADR-007 Consequences).

    docker compose up scheduler
"""

import logging
import os
import time
from collections.abc import Callable
from datetime import UTC, datetime

from app.connectors.gios import client as gios_client
from app.connectors.gios.ingest import ingest_station
from app.connectors.imgw_hydro import client as imgw_hydro_client
from app.connectors.imgw_hydro.ingest import ingest_snapshot as ingest_hydro_snapshot
from app.connectors.imgw_warningshydro import client as imgw_warnings_client
from app.connectors.imgw_warningshydro.ingest import ingest_raw
from app.connectors.open_meteo.ingest import ingest_geo_area
from app.db import SessionLocal
from app.models import GeoArea
from app.provenance import purge_expired_payloads
from app.source_health import collect_source_health, log_health_transitions
from app.source_status import record_source_run

logger = logging.getLogger(__name__)

# ADR-004 verified cycle: Open-Meteo/ICON refreshes every 3h. GIOŚ measurement
# data is hourly. IMGW hydro/warnings cadence isn't documented (ADR-008/009) -
# 1h is a starting assumption, same as GIOŚ, pending real verification.
OPEN_METEO_INTERVAL_SECONDS = 3 * 60 * 60
GIOS_INTERVAL_SECONDS = 60 * 60
IMGW_HYDRO_INTERVAL_SECONDS = 60 * 60
IMGW_WARNINGS_HYDRO_INTERVAL_SECONDS = 60 * 60
# ADR-014: payload retention is coarse (days), so once a day is plenty.
RAW_RETENTION_INTERVAL_SECONDS = 24 * 60 * 60
POLL_INTERVAL_SECONDS = 60


def _gios_station_ids() -> list[str]:
    # ADR-007: which stations to poll is a deliberate, explicit choice (rule #9),
    # never guessed here - comma-separated env var, empty means "skip GIOS".
    raw = os.environ.get("GIOS_STATION_IDS", "")
    return [s.strip() for s in raw.split(",") if s.strip()]


def _last_cause(errors: list[str]) -> str:
    return f"; last cause: {errors[-1]}" if errors else ""


def run_open_meteo() -> bool:
    db = SessionLocal()
    errors: list[str] = []
    try:
        areas = db.query(GeoArea).all()
        failed = sum(ingest_geo_area(area, db, errors) is None for area in areas)
    finally:
        db.close()
    if not areas:
        logger.warning("no geo_areas configured - skipping scheduled Open-Meteo ingest")
        return False  # skipped, not a successful fetch (ADR-012)
    if failed == len(areas):
        # Per-area isolation (rule #1) swallows fetch errors; if EVERY area failed the
        # source is down and this run must not refresh last_success_at (ADR-012,
        # TASK-13.1) - a partial failure still counts as a run.
        raise RuntimeError(f"Open-Meteo failed for all {failed} geo area(s){_last_cause(errors)}")
    return True


def run_gios() -> bool:
    station_ids = _gios_station_ids()
    if not station_ids:
        logger.info("GIOS_STATION_IDS not set - skipping scheduled GIOS ingest")
        return False  # skipped, not a successful fetch (ADR-012)
    db = SessionLocal()
    errors: list[str] = []
    try:
        stations = gios_client.find_stations(set(station_ids))
        failed = sum(ingest_station(station, db, errors) is None for station in stations)
    finally:
        db.close()
    # Per-station isolation (rule #1) swallows errors: configured IDs matching no
    # station, or every station failing, is an outage - not a successful run
    # (ADR-012, TASK-13.1). A partial failure still counts as a run.
    if not stations or failed == len(stations):
        raise RuntimeError(
            f"GIOS: no data fetched ({len(stations)} station(s), {failed} failed)"
            f"{_last_cause(errors)}"
        )
    return True


def run_imgw_hydro() -> None:
    # No station-id gating needed (unlike GIOS): one call returns every station,
    # already deterministic - nothing to guess (ADR-008).
    db = SessionLocal()
    try:
        stations = imgw_hydro_client.fetch_stations()
        _stored, rejected = ingest_hydro_snapshot(stations, db, fetched_at=datetime.now(UTC))
    finally:
        db.close()
    # ADR-012: an empty answer or ANY rejected station is an incomplete snapshot - valid
    # rows are stored, but the run is a failure, not a success (same as warnings).
    if not stations or rejected:
        raise RuntimeError(f"IMGW hydro: incomplete snapshot ({rejected}/{len(stations)} rejected)")


def run_imgw_warningshydro() -> None:
    db = SessionLocal()
    try:
        raw = imgw_warnings_client.fetch_warnings()
        _stored, _expired, rejected = ingest_raw(raw, db, fetched_at=datetime.now(UTC))
    finally:
        db.close()
    if rejected:
        # ADR-012: valid warnings are stored, but the snapshot is incomplete - a
        # rejected warning may be exactly the active one, so this run must not
        # refresh last_success_at (that would let clients show a false all-clear).
        raise RuntimeError(f"{rejected} IMGW warning(s) failed to parse - snapshot incomplete")


def run_raw_retention() -> None:
    """ADR-014: NULL out raw payloads past each source's retention window."""
    db = SessionLocal()
    try:
        purged = purge_expired_payloads(db)
    finally:
        db.close()
    logger.info("raw payload retention: purged %s payload(s)", purged)


def _run_job_safely(
    name: str, job: Callable[[], bool | None], *, track_status: bool = True
) -> None:
    """Rule #1: a connector failure (source down, retry exhausted, bad payload)
    must not take down the scheduler and stop every other source's refresh.
    ADR-012: every run is recorded in source_status (`name` is the source_id); a
    job returning False skipped itself and records nothing. `track_status=False`
    is for housekeeping jobs that are not a data source (no source_status row)."""
    try:
        ran = job()
    except Exception as exc:
        logger.exception("scheduled job %s failed - other jobs still run (rule #1)", name)
        if track_status:
            _record_run(name, success=False, error=f"{type(exc).__name__}: {exc}")
        return
    if track_status and ran is not False:
        _record_run(name, success=True)


def _record_run(source_id: str, *, success: bool, error: str | None = None) -> None:
    # Own session, and never raises: a DB hiccup while recording status must not
    # turn a successful ingest into a crashed scheduler (rule #1).
    db = None
    try:
        db = SessionLocal()
        record_source_run(db, source_id, success=success, error=error)
    except Exception:
        logger.exception("could not record source_status for %s", source_id)
    finally:
        if db is not None:
            db.close()


def _check_source_health(state: dict[str, str]) -> None:
    """TASK-13.1: log STALE/UNAVAILABLE once per state change (anti-spam: `state`
    carries the previous states, in memory like the rest of the scheduler, ADR-007).
    Deliberately disabled sources (GIOS without GIOS_STATION_IDS) are skipped. Never
    raises (rule #1)."""
    db = None
    try:
        db = SessionLocal()
        state.update(log_health_transitions(collect_source_health(db), state))
    except Exception:
        logger.exception("source health check failed")
    finally:
        if db is not None:
            try:
                db.close()
            except Exception:  # broken connection: monitoring must never kill the loop
                logger.exception("could not close source health session")


def main(*, iterations: int | None = None) -> None:
    """iterations caps the loop for tests; None (default) runs forever."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    # -inf, not 0.0: time.monotonic()'s epoch is undefined (docs: "reference point
    # is undefined, only the difference between two calls is valid") - 0.0 happened
    # to work on Linux (monotonic counts from boot, so "now" is usually already
    # hours past either interval) but that's an assumption about the platform, not
    # a guarantee. -inf makes "run on startup" deterministic everywhere.
    last_open_meteo = last_gios = last_imgw_hydro = last_imgw_warnings = float("-inf")
    last_retention = float("-inf")
    health_state: dict[str, str] = {}
    count = 0
    while iterations is None or count < iterations:
        now = time.monotonic()
        if now - last_open_meteo >= OPEN_METEO_INTERVAL_SECONDS:
            _run_job_safely("open_meteo", run_open_meteo)
            last_open_meteo = now
        if now - last_gios >= GIOS_INTERVAL_SECONDS:
            _run_job_safely("gios", run_gios)
            last_gios = now
        if now - last_imgw_hydro >= IMGW_HYDRO_INTERVAL_SECONDS:
            _run_job_safely("imgw_hydro", run_imgw_hydro)
            last_imgw_hydro = now
        if now - last_imgw_warnings >= IMGW_WARNINGS_HYDRO_INTERVAL_SECONDS:
            _run_job_safely("imgw_warningshydro", run_imgw_warningshydro)
            last_imgw_warnings = now
        if now - last_retention >= RAW_RETENTION_INTERVAL_SECONDS:
            _run_job_safely("raw_retention", run_raw_retention, track_status=False)
            last_retention = now
        _check_source_health(health_state)
        count += 1
        if iterations is None or count < iterations:
            time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
