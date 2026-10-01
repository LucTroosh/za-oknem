"""GIOŚ station catalog as an entity + area -> station assignment (ADR-024, TASK-6.2 (7)).

`/station/findAll` is a 2 req/min list endpoint that GIOŚ itself marks as updated yearly
(source-registry), so the scheduler walks it at most once a day (`CATALOG_MAX_AGE`) and
keeps the result in `gios_stations`. Which stations to poll is then derived, not guessed
(rule #9): for every actively polled area (`polling_areas`) the nearest catalog station
within MAX_MATCH_DISTANCE_KM (`geo.select_stations`). `GIOS_STATION_IDS` stays an explicit
override (ADR-007) and bypasses all of this.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import provenance
from app.connectors.gios import client
from app.connectors.gios.parser import PARSER_VERSION, GiosParseError
from app.connectors.open_meteo.ingest import polling_areas
from app.geo import select_stations
from app.models import GiosStation

logger = logging.getLogger(__name__)

CATALOG_MAX_AGE = timedelta(hours=24)


def _parse(station: dict) -> tuple[str, str, float, float]:
    try:
        sid = str(station["Identyfikator stacji"])
        name = str(station["Nazwa stacji"])
        lat, lon = float(station["WGS84 φ N"]), float(station["WGS84 λ E"])
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise GiosParseError(f"malformed catalog station {station!r}: {exc}") from exc
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise GiosParseError(f"catalog station {sid} has out-of-range coordinates")
    return sid, name, lat, lon


def discover_stations(db: Session, *, now: datetime | None = None) -> int:
    """Walk the whole catalog once and upsert it; returns the number of valid stations.
    Raises GiosApiError / GiosParseError (no valid station at all) - the caller decides
    whether a cached catalog is good enough (rule #1)."""
    fetched_at = now or datetime.now(UTC)
    stations = client.fetch_all_stations()
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
    for sid, row in existing.items():
        if sid not in parsed and sid not in listed:
            db.delete(row)
    db.commit()
    return len(parsed)


def ensure_catalog(db: Session, *, now: datetime | None = None) -> bool:
    """Refresh the catalog when it is empty or older than CATALOG_MAX_AGE. Returns True
    when a refresh happened. A failed refresh falls back to the cached catalog (rule #1);
    with no cache at all it raises."""
    now = now or datetime.now(UTC)
    newest = db.query(func.max(GiosStation.fetched_at)).scalar()
    if newest is not None:
        if newest.tzinfo is None:  # SQLite returns naive datetimes
            newest = newest.replace(tzinfo=UTC)
        if now - newest < CATALOG_MAX_AGE:
            return False
    try:
        discover_stations(db, now=now)
        return True
    except (client.GiosApiError, GiosParseError) as exc:
        db.rollback()
        if newest is None:
            raise
        logger.warning(
            "GIOS catalog refresh failed (%s); using cached catalog from %s", exc, newest
        )
        return False


def assigned_station_ids(db: Session) -> list[str]:
    """Station ids to poll: nearest catalog station within the limit for every actively
    polled area, de-duplicated, sorted. Areas with no station in range contribute nothing
    ("brak danych dla obszaru")."""
    points = [(r.station_id, r.latitude, r.longitude) for r in db.query(GiosStation)]
    if not points:
        return []
    return sorted(
        {
            m.station_id
            for area in polling_areas(db)
            for m in select_stations(area.latitude, area.longitude, points)
        }
    )


def stations_by_id(db: Session, ids: list[str]) -> list[dict]:
    """Raw catalog dicts (what `ingest_station` takes) for `ids`, in the given order."""
    rows = {
        r.station_id: r.raw for r in db.query(GiosStation).filter(GiosStation.station_id.in_(ids))
    }
    return [rows[i] for i in ids if i in rows]
