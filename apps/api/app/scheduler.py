"""Minimal loop-based scheduler (ADR-007) — no job table, no queue, no separate
worker process: re-runs the existing connector ingest functions on a fixed
interval, in one process. Swap for a real queue/worker only when a second
replica actually needs to coordinate (see ADR-007 Consequences).

    docker compose up scheduler
"""

import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select

from app.config import warn_if_open_meteo_host_unusual
from app.connectors.gios import client as gios_client
from app.connectors.gios.discovery import (
    AIR_STATIONS_PER_AREA,
    air_areas,
    area_station_ids,
    assigned_station_ids,
    catalog_points,
    ensure_catalog,
    stations_by_id,
)
from app.connectors.gios.ingest import gios_station_ids, ingest_station, run_failure
from app.connectors.imgw_hydro import client as imgw_hydro_client
from app.connectors.imgw_hydro.ingest import ingest_snapshot as ingest_hydro_snapshot
from app.connectors.imgw_hydro.ingest import snapshot_failure
from app.connectors.imgw_warningshydro import client as imgw_warnings_client
from app.connectors.imgw_warningshydro.ingest import ingest_raw
from app.connectors.open_meteo.ingest import (
    ingest_geo_area,
    polling_areas,
    purge_stale_hourly_forecasts,
)
from app.connectors.open_meteo_pollen.ingest import ingest_areas as ingest_pollen_areas
from app.db import SessionLocal
from app.models import GeoArea, Measurement, PollenSnapshot, WeatherSnapshot
from app.places import expire_idle_areas
from app.provenance import purge_expired_payloads
from app.source_health import collect_source_health, log_health_transitions
from app.source_status import (
    SMALL_SET_MAX_FAILED_FRACTION,
    record_source_run,
    run_failure_reason,
)

logger = logging.getLogger(__name__)

# ADR-004 verified cycle: Open-Meteo/ICON refreshes every 3h. GIOŚ measurement
# data is hourly. IMGW hydro/warnings cadence isn't documented (ADR-008/009) -
# 1h is a starting assumption, same as GIOŚ, pending real verification.
OPEN_METEO_INTERVAL_SECONDS = 3 * 60 * 60
# CAMS Europe (pollen via Open-Meteo) is produced once a day - ADR-004/ADR-020.
OPEN_METEO_POLLEN_INTERVAL_SECONDS = 24 * 60 * 60
GIOS_INTERVAL_SECONDS = 60 * 60
IMGW_HYDRO_INTERVAL_SECONDS = 60 * 60
IMGW_WARNINGS_HYDRO_INTERVAL_SECONDS = 60 * 60
# ADR-014: payload retention is coarse (days), so once a day is plenty.
RAW_RETENTION_INTERVAL_SECONDS = 24 * 60 * 60
# The loop tick. Jobs are gated by their own intervals, so a short tick only makes the bootstrap
# of a newly activated place (ADR-029) start within seconds instead of up to a minute.
POLL_INTERVAL_SECONDS = 15
HEALTH_CHECK_INTERVAL_SECONDS = 60
# ADR-029: idle place-areas are switched off once a day (TTL is days, so daily is plenty).
PLACE_EXPIRY_INTERVAL_SECONDS = 24 * 60 * 60
# ADR-029: a freshly activated place gets its first weather/pollen fetch within a minute
# instead of waiting for the 3 h / 24 h cycle. Bounded so a failing area cannot burn budget.
BOOTSTRAP_MAX_ATTEMPTS = 3
BOOTSTRAP_RETRY_SECONDS = 15 * 60
# GIOŚ terms: data is to be downloaded no more often than twice an hour. The air bootstrap is one
# extra fetch of a station that has no data yet, so with the hourly job that is at most two per
# hour; a failed first try is retried by the hourly job, never by a second bootstrap try.
AIR_BOOTSTRAP_MAX_ATTEMPTS = 1
# The GIOŚ client waits ~30 s between sensor-list requests (2 req/min): this bounds one tick to
# about a minute and a half instead of stalling the single scheduler process.
AIR_BOOTSTRAP_STATIONS_PER_TICK = 3
BOOTSTRAP_BATCH = 5  # areas per tick: a burst of activations spreads over ticks, not one stall


def _gios_station_ids() -> list[str]:
    return gios_station_ids()


def _last_cause(errors: list[str]) -> str:
    return f"; last cause: {errors[-1]}" if errors else ""


def run_open_meteo() -> bool:
    db = SessionLocal()
    errors: list[str] = []
    try:
        # ADR-019: only areas with active weather polling (see polling_areas).
        areas = polling_areas(db)
        failed = sum(ingest_geo_area(area, db, errors) is None for area in areas)
    finally:
        db.close()
    if not areas:
        logger.warning("no areas with active weather polling - skipping Open-Meteo ingest")
        return False  # skipped, not a successful fetch (ADR-012)
    # Per-area isolation (rule #1) swallows fetch errors; a failing majority is an
    # outage and must not refresh last_success_at (ADR-012, TASK-13.1).
    reason = run_failure_reason(
        len(areas), failed, max_failed_fraction=SMALL_SET_MAX_FAILED_FRACTION
    )
    if reason:
        raise RuntimeError(f"Open-Meteo: {reason}{_last_cause(errors)}")
    return True


def run_open_meteo_pollen() -> bool:
    # Raises when EVERY geo_area failed (ADR-012: no false success); returns False
    # when there are no polling areas (nothing fetched - not a success either).
    db = SessionLocal()
    try:
        return ingest_pollen_areas(polling_areas(db), db) or False
    finally:
        db.close()


def run_new_area_bootstrap(attempts: dict[int, tuple[int, float]], now: float) -> int:
    """First fetch for place-based areas that are polled but have no weather or no pollen yet
    (ADR-029).
    `attempts` (area id -> (count, monotonic time of the last one)) lives in the scheduler
    loop, in memory like the rest of its state (ADR-007): at most BOOTSTRAP_MAX_ATTEMPTS
    tries, BOOTSTRAP_RETRY_SECONDS apart; after that the regular cycle takes over. Records
    no source_status (that is the regular runs' job). Never raises (rule #1). Returns the
    number of areas attempted."""
    db = None
    try:
        db = SessionLocal()
        # "Needs data" = none yet, or older than one regular cycle: an area re-activated
        # after expiry keeps its old rows, which must not count as "done".
        cutoff_w = datetime.now(UTC) - timedelta(seconds=OPEN_METEO_INTERVAL_SECONDS)
        cutoff_p = datetime.now(UTC) - timedelta(seconds=OPEN_METEO_POLLEN_INTERVAL_SECONDS)
        last_w = (
            select(func.max(WeatherSnapshot.fetched_at))
            .where(WeatherSnapshot.geo_area_id == GeoArea.id)
            .scalar_subquery()
        )
        last_p = (
            select(func.max(PollenSnapshot.fetched_at))
            .where(PollenSnapshot.geo_area_id == GeoArea.id)
            .scalar_subquery()
        )
        no_weather = or_(last_w.is_(None), last_w < cutoff_w)
        no_pollen = or_(last_p.is_(None), last_p < cutoff_p)
        rows = db.execute(
            select(GeoArea, no_weather, no_pollen).where(
                GeoArea.weather_polling_active.is_(True),
                GeoArea.place_id.is_not(None),
                no_weather | no_pollen,
            )
        ).all()
        for stale in set(attempts) - {a.id for a, _, _ in rows}:
            del attempts[stale]  # fresh data landed: a later re-activation may retry
        due = [
            (a, need_weather, need_pollen)
            for a, need_weather, need_pollen in rows
            if attempts.get(a.id, (0, float("-inf")))[0] < BOOTSTRAP_MAX_ATTEMPTS
            and now - attempts.get(a.id, (0, float("-inf")))[1] >= BOOTSTRAP_RETRY_SECONDS
        ]
        for area, need_weather, need_pollen in due[:BOOTSTRAP_BATCH]:
            count = attempts.get(area.id, (0, 0.0))[0]
            attempts[area.id] = (count + 1, now)
            # Each part is retried on its own: a pollen failure after a successful weather
            # fetch must not stop the next attempt (weather existing is not "done").
            if need_weather:
                ingest_geo_area(area, db)  # failure is logged inside, per area (rule #1)
            if need_pollen:
                try:
                    ingest_pollen_areas([area], db)
                except Exception:
                    logger.exception("bootstrap: pollen for %s failed", area.slug)
                    db.rollback()  # a DB error would poison the shared session for the next area
        return min(len(due), BOOTSTRAP_BATCH)
    except Exception:
        logger.exception("new-area bootstrap failed - regular cycle still runs (rule #1)")
        if db is not None:
            db.rollback()
        return 0
    finally:
        if db is not None:
            db.close()


def run_new_area_air_bootstrap(attempts: dict[str, tuple[int, float]], now: float) -> int:
    """First air fetch for a freshly activated place (ADR-029, amended).

    The hourly GIOŚ job only learns a new area's stations at its next run, and until then the
    API can only offer a station polled for some other area - possibly 100 km away
    ("regional"). So for place-based areas whose nearest AIR_STATIONS_PER_AREA catalog stations
    have no measurement yet, those stations are fetched now.

    Bounds, all per STATION (a station shared by areas is one request, not one per area):
    - ONE attempt per station (AIR_BOOTSTRAP_MAX_ATTEMPTS): GIOŚ allows downloading at most
      twice an hour and the hourly job is the retry, so a station that never yields data (no
      sensors, GIOŚ 400) costs one extra fetch. `attempts` lives in the loop (station id ->
      (count, time of the last one)).
    - AIR_BOOTSTRAP_STATIONS_PER_TICK stations per tick: the GIOŚ client waits ~30 s between
      sensor-list requests, so a tick must stay short or it would stall the single scheduler
      process. Order: the nearest station of every area first, then the second nearest...
    Skipped when GIOS_STATION_IDS is set (the explicit station list is the exact allowed set,
    ADR-007) and without a catalog (its first walk belongs to the hourly job, 2 req/min).
    Records no source_status; never raises (rule #1). Returns the number of stations fetched."""
    if _gios_station_ids():
        return 0
    db = None
    try:
        db = SessionLocal()
        points = catalog_points(db)
        if not points:
            return 0
        wanted = {
            area.id: ids
            for area in air_areas(db)
            if area.place_id is not None and (ids := area_station_ids(area, points))
        }
        all_ids = {sid for ids in wanted.values() for sid in ids}
        have = set(
            db.execute(
                select(Measurement.station_id)
                .where(Measurement.source_id == "gios", Measurement.station_id.in_(all_ids))
                .distinct()
            ).scalars()
        )
        missing = all_ids - have
        for stale in set(attempts) - missing:
            del attempts[
                stale
            ]  # data landed (or no area wants it): a later re-activation may retry
        ordered: list[str] = []  # nearest-of-every-area first; area id order breaks ties
        for rank in range(AIR_STATIONS_PER_AREA):
            for aid in sorted(wanted):
                ids = wanted[aid]
                if rank < len(ids) and ids[rank] in missing and ids[rank] not in ordered:
                    ordered.append(ids[rank])
        due = [
            sid
            for sid in ordered
            if attempts.get(sid, (0, float("-inf")))[0] < AIR_BOOTSTRAP_MAX_ATTEMPTS
            and now - attempts.get(sid, (0, float("-inf")))[1] >= BOOTSTRAP_RETRY_SECONDS
        ][:AIR_BOOTSTRAP_STATIONS_PER_TICK]
        for sid in due:
            attempts[sid] = (attempts.get(sid, (0, 0.0))[0] + 1, now)
        for station in stations_by_id(db, due):
            try:
                ingest_station(station, db)  # per-station failure is logged inside (rule #1)
            except Exception:
                logger.exception(
                    "air bootstrap: station %s failed", station.get("Identyfikator stacji")
                )
                db.rollback()
        return len(due)
    except Exception:
        logger.exception("new-area air bootstrap failed - regular cycle still runs (rule #1)")
        if db is not None:
            db.rollback()
        return 0
    finally:
        if db is not None:
            db.close()


def run_place_expiry() -> None:
    """ADR-029: stop polling place-based areas nobody re-activated within the TTL."""
    db = SessionLocal()
    try:
        expired = expire_idle_areas(db)
    finally:
        db.close()
    logger.info("place expiry: %s idle area(s) no longer polled", expired)


def run_gios() -> bool:
    station_ids = _gios_station_ids()
    db = SessionLocal()
    errors: list[str] = []
    try:
        if station_ids:
            # GIOS_STATION_IDS = explicit override (ADR-007): exactly these stations.
            wanted = set(station_ids)
            stations = gios_client.find_stations(wanted)
        else:
            # ADR-025: stations derived from the actively polled areas (nearest within the
            # distance limit) via the cached catalog, refreshed at most daily.
            if not air_areas(db):  # nothing to serve: no catalog walk either
                logger.info("no areas with active polling - skipping GIOS ingest")
                return False
            ensure_catalog(db)
            ids = assigned_station_ids(db)
            if not ids:
                logger.info("no GIOS station assigned to any polling area - skipping GIOS ingest")
                return False  # skipped, not a successful fetch (ADR-012)
            wanted = set(ids)
            stations = stations_by_id(db, ids)
        failed = sum(ingest_station(station, db, errors) is None for station in stations)
    finally:
        db.close()
    # Per-station isolation (rule #1) swallows errors: a failing majority of the CONFIGURED
    # stations (unmatched ids included) is an outage, not a success (ADR-012, TASK-13.1).
    failure = run_failure(wanted, stations, failed, errors)
    if failure:
        raise RuntimeError(f"{failure}{_last_cause(errors)}")
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
    # No successes or more than 2% rejected = failed run; below that the run counts and
    # the rejected ids are logged by ingest_snapshot (ADR-012 Consequences).
    failure = snapshot_failure(stations, rejected)
    if failure:
        raise RuntimeError(failure)


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
    """ADR-014: NULL out raw payloads past each source's retention window. ADR-030: same
    daily housekeeping drops hourly forecast rows left behind by areas that stopped being
    polled."""
    db = SessionLocal()
    purged = hourly = 0
    try:
        # Independent steps: a failing payload purge must not skip the hourly cleanup (#1).
        try:
            purged = purge_expired_payloads(db)
        except Exception:
            logger.exception("raw payload retention failed")
            db.rollback()
        try:
            hourly = purge_stale_hourly_forecasts(db)
        except Exception:
            logger.exception("hourly forecast retention failed")
            db.rollback()
    finally:
        db.close()
    logger.info(
        "raw payload retention: purged %s payload(s), %s stale hourly forecast row(s)",
        purged,
        hourly,
    )


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
        new_state = log_health_transitions(collect_source_health(db), state)
        state.clear()  # replace, not merge: a source that stopped being monitored must
        state.update(new_state)  # lose its cached state, or re-enabling suppresses the log
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
    warn_if_open_meteo_host_unusual()
    # -inf, not 0.0: time.monotonic()'s epoch is undefined (docs: "reference point
    # is undefined, only the difference between two calls is valid") - 0.0 happened
    # to work on Linux (monotonic counts from boot, so "now" is usually already
    # hours past either interval) but that's an assumption about the platform, not
    # a guarantee. -inf makes "run on startup" deterministic everywhere.
    last_open_meteo = last_open_meteo_pollen = last_gios = last_imgw_hydro = last_imgw_warnings = (
        float("-inf")
    )
    last_retention = last_place_expiry = float("-inf")
    bootstrap_attempts: dict[int, tuple[int, float]] = {}
    air_bootstrap_attempts: dict[str, tuple[int, float]] = {}
    last_health = float("-inf")
    health_state: dict[str, str] = {}
    count = 0
    while iterations is None or count < iterations:
        now = time.monotonic()
        # First: an area whose TTL elapsed must not be polled once more (ADR-029).
        if now - last_place_expiry >= PLACE_EXPIRY_INTERVAL_SECONDS:
            _run_job_safely("place_expiry", run_place_expiry, track_status=False)
            last_place_expiry = now
        if now - last_open_meteo >= OPEN_METEO_INTERVAL_SECONDS:
            _run_job_safely("open_meteo", run_open_meteo)
            last_open_meteo = now
        if now - last_open_meteo_pollen >= OPEN_METEO_POLLEN_INTERVAL_SECONDS:
            _run_job_safely("open_meteo_pollen", run_open_meteo_pollen)
            last_open_meteo_pollen = now
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
        run_new_area_bootstrap(bootstrap_attempts, now)
        run_new_area_air_bootstrap(air_bootstrap_attempts, now)
        if now - last_health >= HEALTH_CHECK_INTERVAL_SECONDS:
            _check_source_health(health_state)
            last_health = now
        count += 1
        if iterations is None or count < iterations:
            time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
