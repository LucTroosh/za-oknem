"""GIOŚ station catalog as an entity + area -> station assignment (ADR-025, TASK-6.2 (7)).

`/station/findAll` is a 2 req/min list endpoint that GIOŚ itself marks as updated yearly
(source-registry), so the scheduler walks it at most once a day (`CATALOG_MAX_AGE`) and
keeps the result in `gios_stations`. Which stations to poll is then derived, not guessed
(rule #9): for every actively polled area (`polling_areas`) the nearest catalog station
within MAX_MATCH_DISTANCE_KM (`geo.select_stations`). `GIOS_STATION_IDS` stays an explicit
override (ADR-007) and bypasses all of this.
"""

import logging
import math
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, defer

from app import provenance
from app.connectors.gios import client
from app.connectors.gios.ingest import gios_station_ids
from app.connectors.gios.parser import PARSER_VERSION, GiosParseError
from app.connectors.open_meteo.ingest import polling_areas
from app.geo import REGIONAL_MAX_KM, select_stations
from app.models import GiosStation

logger = logging.getLogger(__name__)

CATALOG_MAX_AGE = timedelta(hours=24)
# Last failed refresh while a cached catalog exists: the hourly job must not re-walk the
# rate-limited catalog every hour during an outage - retry once per CATALOG_MAX_AGE.
# ponytail: in-process (the scheduler is one process, ADR-007); a restart retries at once.
# Persist it (e.g. in source_status) if the scheduler ever restarts often or runs replicated.
_last_failed_refresh: datetime | None = None


def _parse(station: dict) -> tuple[str, str, float, float]:
    try:
        raw_id = station["Identyfikator stacji"]
        if raw_id is None or not str(raw_id).strip() or isinstance(raw_id, bool):
            raise ValueError("empty station id")
        sid = str(raw_id).strip()
        name = str(station["Nazwa stacji"])
        lat, lon = float(station["WGS84 φ N"]), float(station["WGS84 λ E"])
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise GiosParseError(f"malformed catalog station {station!r}: {exc}") from exc
    if not (math.isfinite(lat) and math.isfinite(lon)):
        raise GiosParseError(f"catalog station {sid} has non-finite coordinates")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise GiosParseError(f"catalog station {sid} has out-of-range coordinates")
    return sid, name, lat, lon


def discover_stations(db: Session, *, now: datetime | None = None) -> int:
    """Walk the whole catalog once and upsert it; returns the number of valid stations.
    Raises GiosApiError / GiosParseError (no valid station at all) - the caller decides
    whether a cached catalog is good enough (rule #1)."""
    fetched_at = now or datetime.now(UTC)
    try:
        stations = client.fetch_all_stations()
    except (TypeError, AttributeError) as exc:  # valid JSON of the wrong shape (null pages...)
        raise client.GiosApiError(f"unexpected findAll response shape: {exc}") from exc
    fetch_id = provenance.record_fetch(
        db,
        source_id="gios",
        endpoint=f"{client.BASE_URL}/station/findAll",
        payload={"stations": stations},
        fetched_at=fetched_at,
        parser_version=PARSER_VERSION,
    )
    parsed: dict[str, tuple[str, float, float, dict]] = {}
    rejected = 0
    for station in stations:
        try:
            sid, name, lat, lon = _parse(station)
        except GiosParseError as exc:
            rejected += 1
            logger.warning("GIOS catalog: rejected station (%s)", exc)
            continue
        parsed[sid] = (name, lat, lon, station)
    status = provenance.INVALID if not parsed else provenance.batch_status(len(stations), rejected)
    provenance.set_validation_status(db, fetch_id, status)
    if not parsed:
        raise GiosParseError("catalog contains no valid stations")

    existing = {row.station_id: row for row in db.query(GiosStation)}
    for sid, (name, lat, lon, raw) in parsed.items():
        row = existing.get(sid) or GiosStation(station_id=sid)
        row.station_name, row.latitude, row.longitude, row.raw = name, lat, lon, raw
        row.fetched_at, row.source_fetch_id = fetched_at, fetch_id
        db.add(row)
    # A station GIOŚ no longer lists must stop being assigned. Rejected-but-listed ones
    # keep their previous row (a parse problem is not a removal) - only unlisted go.
    listed = {str(s.get("Identyfikator stacji")) for s in stations if isinstance(s, dict)}
    # ponytail: a walk that silently stopped early (e.g. a page without `totalPages`) looks
    # like a mass removal - prune only when the new snapshot keeps at least half of the cache.
    # Proper fix: make client._iter_station_pages require pagination metadata.
    if len(listed) * 2 >= len(existing):
        for sid, row in existing.items():
            if sid not in parsed and sid not in listed:
                db.delete(row)
    else:
        logger.warning("GIOS catalog shrank %s -> %s: not pruning", len(existing), len(listed))
    db.commit()
    return len(parsed)


def ensure_catalog(db: Session, *, now: datetime | None = None) -> bool:
    """Refresh the catalog when it is empty or older than CATALOG_MAX_AGE. Returns True
    when a refresh happened. A failed refresh falls back to the cached catalog (rule #1) and
    is not retried for CATALOG_MAX_AGE; with no cache at all it raises (and retries each run)."""
    global _last_failed_refresh
    now = now or datetime.now(UTC)
    newest = db.query(func.max(GiosStation.fetched_at)).scalar()
    if newest is not None:
        if newest.tzinfo is None:  # SQLite returns naive datetimes
            newest = newest.replace(tzinfo=UTC)
        if now - newest < CATALOG_MAX_AGE:
            return False
        if _last_failed_refresh and now - _last_failed_refresh < CATALOG_MAX_AGE:
            return False
    try:
        discover_stations(db, now=now)
        _last_failed_refresh = None
        return True
    except (client.GiosApiError, GiosParseError) as exc:
        db.rollback()
        if newest is None:
            raise
        _last_failed_refresh = now
        logger.warning(
            "GIOS catalog refresh failed (%s); using cached catalog from %s", exc, newest
        )
        return False


def assigned_station_ids(db: Session) -> list[str]:
    """Station ids to poll: nearest catalog station within REGIONAL_MAX_KM (ADR-029: the
    50-100 km "regional" band is polled too, so it has data to disclose) for every actively
    polled area, de-duplicated, sorted. Areas with no station in range contribute nothing
    ("brak danych dla obszaru")."""
    rows = db.query(GiosStation).options(defer(GiosStation.raw))  # raw JSON not needed here
    points = [(r.station_id, r.latitude, r.longitude) for r in rows]
    if not points:
        return []
    return sorted(
        {
            m.station_id
            for area in polling_areas(db)
            for m in select_stations(area.latitude, area.longitude, points, max_km=REGIONAL_MAX_KM)
        }
    )


def stations_by_id(db: Session, ids: list[str]) -> list[dict]:
    """Raw catalog dicts (what `ingest_station` takes) for `ids`, in the given order."""
    rows = {
        r.station_id: r.raw for r in db.query(GiosStation).filter(GiosStation.station_id.in_(ids))
    }
    return [rows[i] for i in ids if i in rows]


def assignment_candidates(db: Session, stations: dict[str, dict]) -> list[tuple[str, float, float]]:
    """(id, lat, lon) points the API may assign, from `stations` (id -> row with latitude/
    longitude, i.e. the ones that have measurements). Once a catalog exists it is the
    authority: only catalog stations qualify, at their CATALOG coordinates (the ones polling
    assignment used), plus stations named in the GIOS_STATION_IDS override (fetched
    live, so even if also catalogued) at their measured coordinates.
    A station GIOŚ dropped from the catalog is therefore never
    assigned on the strength of its old measurements. No catalog yet = legacy setup:
    measured coordinates, no filtering."""
    catalog = {
        r.station_id: (r.latitude, r.longitude)
        for r in db.execute(select(GiosStation).options(defer(GiosStation.raw))).scalars().all()
    }
    override = set(gios_station_ids())
    points: list[tuple[str, float, float]] = []
    for sid, s in stations.items():
        # Override stations are fetched live each run (catalog row may be stale) -> measured.
        if sid in override or not catalog:
            points.append((sid, s["latitude"], s["longitude"]))
        elif sid in catalog:
            points.append((sid, *catalog[sid]))
    return points


def polling_expected(db: Session) -> bool:
    """Whether GIOS is meant to run (source_health `monitored`): an env override, an
    assignment, or - while the catalog is still empty - any actively polled area, so a
    failing first discovery stays visible instead of looking like a disabled source."""
    if gios_station_ids():
        return True
    if db.query(GiosStation.id).first() is not None:
        return bool(assigned_station_ids(db))
    return bool(polling_areas(db))
