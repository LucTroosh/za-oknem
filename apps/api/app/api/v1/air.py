from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.air_index import air_index
from app.attribution import GIOS_ATTRIBUTION
from app.connectors.gios.discovery import assignment_candidates
from app.db import get_db
from app.geo import classify_air_coverage, coverage_radius_km, pick_air_station
from app.models import GeoArea, Measurement

router = APIRouter()

# Thresholds for freshness status (Principle 3 / §42). PM2.5 station data updates
# roughly hourly in practice — not yet verified via ADR-004, conservative for now.
FRESH_MAX_AGE = timedelta(hours=2)
RECENT_MAX_AGE = timedelta(hours=6)


def freshness(observed_at: datetime) -> str:
    age = datetime.now(UTC) - observed_at
    if age <= FRESH_MAX_AGE:
        return "FRESH"
    if age <= RECENT_MAX_AGE:
        return "RECENT"
    return "STALE"


# TASK-API-1: response_model - documents the real OpenAPI shape and makes FastAPI
# validate every response against it (a shape regression now 500s instead of
# silently shipping a wrong key to mobile). Mirrors the existing dict shape
# exactly - no API change.
class AirParam(BaseModel):
    value: float
    unit: str
    observed_at: str
    freshness: Literal["FRESH", "RECENT", "STALE"]


IndexLevel = Literal["GOOD", "FAIR", "MODERATE", "POOR", "VERY_POOR", "EXTREMELY_POOR"]


class AirIndex(BaseModel):
    """European AQI (app/air_index.py, ADR-015). `level` None = "no index" (never a
    default GOOD); DERIVED, not a Measurement (rule #7)."""

    level: IndexLevel | None
    complete: bool
    params: dict[str, IndexLevel]
    dominant: list[str]
    missing: dict[str, Literal["MISSING", "STALE", "UNIT", "INVALID"]]
    valid_until: str | None


class AirStation(BaseModel):
    station_id: str
    station_name: str
    latitude: float
    longitude: float
    params: dict[str, AirParam]
    # Additive field: a client that ignores it keeps working.
    index: AirIndex
    source: Literal["gios"]
    # Only with ?geo_area_id= (ADR-025): provenance of the area -> station assignment.
    distance_km: float | None = None
    assignment_method: str | None = None
    # ADR-029: exact (<=10 km) | nearby (<=50) | regional (<=100, far-away station).
    coverage: Literal["exact", "nearby", "regional"] | None = None
    coverage_radius_km: int | None = None


class AirLatestResponse(BaseModel):
    stations: list[AirStation]


def assign_air_station(db: Session, area: GeoArea, stations: dict[str, dict]) -> dict | None:
    """ADR-025 assignment of the area's air station, shared by /air/latest and /air/history so
    both always show the SAME station: nearest WITH data, within REGIONAL_MAX_KM, at the catalog
    position. `stations` = id -> {latitude, longitude} of those that have measurements."""
    points = assignment_candidates(db, stations)
    coords = {sid: (lat, lon) for sid, lat, lon in points}
    match, _ = pick_air_station(area.latitude, area.longitude, points, set(stations))
    if match is None:  # no station WITH data in range (ADR-025 amended)
        return None
    level = classify_air_coverage(match.distance_km)
    return {
        "station_id": match.station_id,
        "coverage": level,
        "coverage_radius_km": coverage_radius_km(level),
        # the position the distance was computed from (catalog), not the measured one
        "latitude": coords[match.station_id][0],
        "longitude": coords[match.station_id][1],
        "distance_km": round(match.distance_km, 1),
        "assignment_method": match.method,
    }


# exclude_unset: the ADR-025 provenance fields appear only for ?geo_area_id= - the plain list
# keeps its exact old shape (explicit nulls such as index.level stay, they are "set").
@router.get("/air/latest", response_model=AirLatestResponse, response_model_exclude_unset=True)
def latest_air_quality(
    geo_area_id: int | None = Query(None, ge=1, le=2_147_483_647), db: Session = Depends(get_db)
) -> dict:
    """Reads only from our own DB (rule #14) — never calls GIOŚ on request.
    Data arrives via `python -m app.connectors.gios.ingest` (manual for now, Phase 4).

    TASK-4.1: full MVP param set (PM2.5/PM10/NO2/SO2/O3/CO/C6H6), not just PM2.5 —
    each station now returns a `params` dict keyed by param code instead of a single
    top-level `pm25` field.

    ADR-025: `?geo_area_id=N` narrows the list to the station assigned to that area
    (nearest WITH data within REGIONAL_MAX_KM = 100 km, with `distance_km`,
    `assignment_method` and the ADR-029 `coverage` band); no station in range = empty list
    ("brak danych dla obszaru"), unknown area = 404."""
    area = None
    if geo_area_id is not None:
        area = db.get(GeoArea, geo_area_id)
        if area is None:
            raise HTTPException(status_code=404, detail="geo_area not found")
    # Latest reading per (station, param): one query, no N+1 — distinct on
    # (station_id, param_code) ordered by observed_at desc is the standard Postgres
    # idiom for "latest per group", extended to two grouping columns.
    #
    # ponytail: newer SQLAlchemy (2.1+) deprecates this expression-based .distinct()
    # in favor of sqlalchemy.dialects.postgresql.distinct_on(), but the exact new
    # API shape wasn't reliably verifiable from docs at the time of writing (worth
    # confirming against the real changelog, not guessing, before switching — same
    # lesson as the GIOŚ connector). Still correct and fully covered by tests, just
    # noisy in pytest output. Upgrade when SQLAlchemy actually removes the old form.
    # source_id filter: `measurements` is shared with other connectors (e.g.
    # imgw_hydro's water_level_cm) — without it this query would also return
    # river-gauge rows here, labeled as GIOŚ air stations (Codex review).
    stmt = (
        select(Measurement)
        .where(Measurement.source_id == "gios")
        .distinct(Measurement.station_id, Measurement.param_code)
        .order_by(Measurement.station_id, Measurement.param_code, Measurement.observed_at.desc())
    )
    rows = db.execute(stmt).scalars().all()

    if not rows:
        # no data != zero (Principle §43) — empty list, not fabricated 0s
        return {"stations": []}

    stations: dict[str, dict] = {}
    for row in rows:
        station = stations.setdefault(
            row.station_id,
            {
                "station_id": row.station_id,
                "station_name": row.station_name,
                "latitude": row.latitude,
                "longitude": row.longitude,
                "params": {},
                "source": "gios",
            },
        )
        station["params"][row.param_code] = {
            "value": row.value,
            "unit": row.unit,
            "observed_at": row.observed_at.isoformat(),
            "freshness": freshness(row.observed_at),
        }

    for station in stations.values():
        station["index"] = air_index(station["params"], RECENT_MAX_AGE)
    if area is None:
        return {"stations": list(stations.values())}
    # ADR-025: catalog = authority for who may be assigned and at which coordinates.
    assigned = assign_air_station(db, area, stations)
    if assigned is None:
        return {"stations": []}
    return {"stations": [{**stations[assigned["station_id"]], **assigned}]}


# ---- short history (GIOS-03b): the last hours of ONE parameter at the area's station -----------
# Measurements only (rule #7: not a forecast), straight from our DB (rule #14). The source gives
# hourly values, so a spacing well beyond an hour is a visible gap, never an interpolated line.
HISTORY_INTERVAL_MINUTES = 60
GAP_AFTER = timedelta(minutes=90)  # more than 1.5 intervals between two readings = a gap

AirParamCode = Literal["PM2.5", "PM10", "NO2", "SO2", "O3", "CO", "C6H6"]


class AirHistoryPoint(BaseModel):
    observed_at: str
    value: float


class AirHistoryGap(BaseModel):
    after: str  # observed_at of the reading before the gap
    before: str  # observed_at of the reading after it
    missing_hours: int


class AirHistoryStation(BaseModel):
    station_id: str
    station_name: str
    latitude: float
    longitude: float
    distance_km: float
    coverage: Literal["exact", "nearby", "regional"]
    coverage_radius_km: int | None
    assignment_method: str


class AirHistoryResponse(BaseModel):
    kind: Literal["measurement_history"]
    # available: points shown; no_station: no station with data within range of this area;
    # no_data: the area's station has no readings of this parameter in the window (never a zero)
    availability: Literal["available", "no_station", "no_data"]
    param: AirParamCode
    unit: str | None
    hours: int
    window_start: str
    window_end: str
    interval_minutes: int
    station: AirHistoryStation | None
    points: list[AirHistoryPoint]
    gaps: list[AirHistoryGap]
    latest_observed_at: str | None
    latest_freshness: Literal["FRESH", "RECENT", "STALE"] | None
    attribution: str


def _aware(moment: datetime) -> datetime:
    """SQLite hands naive datetimes back; Postgres keeps the offset. Stored times are absolute."""
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


def history_gaps(times: list[datetime]) -> list[dict]:
    """Where consecutive readings are further apart than GAP_AFTER (rule #8: missing hours are
    shown as missing). `times` ascending."""
    gaps = []
    for earlier, later in zip(times, times[1:], strict=False):
        if later - earlier > GAP_AFTER:
            missing = round((later - earlier) / timedelta(minutes=HISTORY_INTERVAL_MINUTES)) - 1
            gaps.append(
                {
                    "after": earlier.isoformat(),
                    "before": later.isoformat(),
                    "missing_hours": max(missing, 1),
                }
            )
    return gaps


@router.get("/air/history", response_model=AirHistoryResponse)
def air_history(
    geo_area_id: int = Query(ge=1, le=2_147_483_647),
    param: AirParamCode = "PM2.5",
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
) -> dict:
    """The last `hours` of one parameter at the station assigned to the area (the same one
    /air/latest shows). Reads only our own DB (rule #14); readings accumulate from every ingest
    (the source itself keeps only ~66 h), so a window longer than what we collected is simply
    shorter, and holes inside it are reported as `gaps`. Unknown area = 404."""
    area = db.get(GeoArea, geo_area_id)
    if area is None:
        raise HTTPException(status_code=404, detail="geo_area not found")
    now = datetime.now(UTC)
    start = now - timedelta(hours=hours)
    base: dict = {
        "kind": "measurement_history",
        "param": param,
        "hours": hours,
        "window_start": start.isoformat(),
        "window_end": now.isoformat(),
        "interval_minutes": HISTORY_INTERVAL_MINUTES,
        "station": None,
        "points": [],
        "gaps": [],
        "unit": None,
        "latest_observed_at": None,
        "latest_freshness": None,
        "attribution": GIOS_ATTRIBUTION,
    }

    # Stations that have any GIOŚ reading, with their measured position (as /air/latest)
    measured = {
        sid: {"latitude": lat, "longitude": lon}
        for sid, lat, lon in db.execute(
            select(
                Measurement.station_id,
                func.max(Measurement.latitude),
                func.max(Measurement.longitude),
            )
            .where(Measurement.source_id == "gios")
            .group_by(Measurement.station_id)
        )
    }
    assigned = assign_air_station(db, area, measured) if measured else None
    if assigned is None:
        return {**base, "availability": "no_station"}

    rows = db.execute(
        select(Measurement)
        .where(
            Measurement.source_id == "gios",
            Measurement.station_id == assigned["station_id"],
            Measurement.param_code == param,
            Measurement.observed_at >= start,
            Measurement.observed_at <= now,  # a future-dated reading is not part of the window
        )
        .order_by(Measurement.observed_at, Measurement.id)
    ).scalars()
    by_time: dict[datetime, Measurement] = {}
    for row in rows:  # two sensors of one parameter must not double a point: first wins
        by_time.setdefault(_aware(row.observed_at), row)
    times = sorted(by_time)

    first = next(iter(by_time.values()), None)
    name = first.station_name if first else None
    if name is None:  # the station exists but sent nothing of this parameter in the window
        name = db.execute(
            select(Measurement.station_name)
            .where(
                Measurement.source_id == "gios", Measurement.station_id == assigned["station_id"]
            )
            .limit(1)
        ).scalar_one()
    keep = ("latitude", "longitude", "distance_km", "coverage")
    station = {
        "station_id": assigned["station_id"],
        "station_name": name,
        **{k: assigned[k] for k in keep},
        "coverage_radius_km": assigned["coverage_radius_km"],
        "assignment_method": assigned["assignment_method"],
    }
    if not times:
        return {**base, "availability": "no_data", "station": station}
    return {
        **base,
        "availability": "available",
        "station": station,
        "unit": by_time[times[0]].unit,
        "points": [{"observed_at": t.isoformat(), "value": by_time[t].value} for t in times],
        "gaps": history_gaps(times),
        "latest_observed_at": times[-1].isoformat(),
        "latest_freshness": freshness(times[-1]),
    }
