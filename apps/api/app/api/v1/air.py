from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.air_index import air_index
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
    `assignment_method` and the ADR-029 `coverage` band); no station in range = empty list ("brak danych dla obszaru"),
    unknown area = 404."""
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
    points = assignment_candidates(db, stations)
    coords = {sid: (lat, lon) for sid, lat, lon in points}
    match, _ = pick_air_station(area.latitude, area.longitude, points, set(stations))
    if match is None:  # no station WITH data in range (ADR-025 amended)
        return {"stations": []}
    level = classify_air_coverage(match.distance_km)
    return {
        "stations": [
            {
                **stations[match.station_id],
                "coverage": level,
                "coverage_radius_km": coverage_radius_km(level),
                # the position the distance was computed from (catalog), not the measured one
                "latitude": coords[match.station_id][0],
                "longitude": coords[match.station_id][1],
                "distance_km": round(match.distance_km, 1),
                "assignment_method": match.method,
            }
        ]
    }
