"""Deterministic geo matching (rule #9, never "na oko").

Two distinct methods, deliberately not mixed (BACKLOG TASK-6.2, ADR-019):
- `haversine_km`: nearest station/point (ADR-006) - for data geography.
- `resolve_gmina`: point-in-polygon - the ONLY method for administrative membership.
"""

import math
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import text
from sqlalchemy.orm import Session

EARTH_RADIUS_KM = 6371.0

# ADR-006/ADR-025: nearest-station match is only valid within this distance (inclusive).
# Beyond it the area has NO station ("brak danych dla obszaru") - never a "nearest" fallback.
MAX_MATCH_DISTANCE_KM = 50.0
METHOD_NEAREST_STATION = "nearest_station"

# ADR-029: air coverage ladder, by distance from the area centre to the assigned station
# (inclusive upper bounds, on the distance rounded to 1 m - the number the client sees).
# exact/nearby are measurements "around" the place; regional (50-100 km) is a far-away
# station disclosed as such and never trusted for the outdoor verdict; beyond = none.
EXACT_MAX_KM = 10.0
NEARBY_MAX_KM = MAX_MATCH_DISTANCE_KM
REGIONAL_MAX_KM = 100.0
AirCoverage = Literal["exact", "nearby", "regional", "none"]

# ADR-026: GPS/manual point -> app area. `point_in_polygon` = the gmina itself (ADR-019);
# `nearest_area` = fallback to the closest ACTIVE area within this distance (inclusive),
# always disclosed with its distance - it never replaces the administrative answer.
METHOD_POINT_IN_POLYGON: Literal["point_in_polygon"] = "point_in_polygon"
METHOD_NEAREST_AREA: Literal["nearest_area"] = "nearest_area"
NEAREST_AREA_MAX_KM = 25.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in kilometers."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


@dataclass(frozen=True)
class StationMatch:
    station_id: str
    distance_km: float
    method: str = METHOD_NEAREST_STATION


def select_stations(
    latitude: float,
    longitude: float,
    stations: Iterable[tuple[str, float, float]],
    *,
    max_km: float = MAX_MATCH_DISTANCE_KM,
    limit: int = 1,
) -> list[StationMatch]:
    """Pure, deterministic point -> stations (rule #9, ADR-025). `stations` are
    (station_id, lat, lon). Only stations within `max_km` (inclusive) qualify; result is
    sorted by distance rounded to 1 m (the limit itself is checked unrounded), ties broken
    by station id (digit ids in numeric order), so input order never changes the outcome.
    Empty list = no data for the area."""
    scored = []
    for sid, lat, lon in stations:
        km = haversine_km(latitude, longitude, lat, lon)
        if km <= max_km:  # cutoff on the exact distance; rounding is only for ranking/output
            scored.append((round(km, 3), sid))
    scored.sort(key=lambda t: (t[0], not t[1].isdigit(), len(t[1]), t[1]))
    return [StationMatch(sid, km) for km, sid in scored[:limit]]


def classify_air_coverage(distance_km: float | None) -> AirCoverage:
    """Pure ladder (rule #9): None (no station within REGIONAL_MAX_KM) or > 100 km = none."""
    if distance_km is None:
        return "none"
    km = round(distance_km, 1)  # the precision clients see: "50.0" must never be "regional"
    if km > REGIONAL_MAX_KM:
        return "none"
    if km <= EXACT_MAX_KM:
        return "exact"
    return "nearby" if km <= NEARBY_MAX_KM else "regional"


def coverage_radius_km(level: AirCoverage) -> int | None:
    """The radius the client may quote ("w promieniu ~50 km"); None for none."""
    return {"exact": 10, "nearby": 50, "regional": 100, "none": None}[level]


def nearest_area(
    latitude: float,
    longitude: float,
    areas: Iterable[tuple[int, float, float]],
    *,
    max_km: float = NEAREST_AREA_MAX_KM,
) -> tuple[int, float] | None:
    """Pure, deterministic point -> (geo_area_id, distance_km) of the nearest area within
    `max_km` (inclusive), ties by lowest id; None = out of range. `areas` are
    (geo_area_id, lat, lon). Same rule as `select_stations` (reused, not copied)."""
    match = select_stations(
        latitude, longitude, ((str(i), la, lo) for i, la, lo in areas), max_km=max_km
    )
    return (int(match[0].station_id), match[0].distance_km) if match else None


@dataclass(frozen=True)
class ResolvedArea:
    geo_area_id: int
    teryt_code: str
    slug: str
    name: str


# ST_Covers (not ST_Contains): a point exactly on a boundary belongs to the polygon, so
# it is never "nowhere". A point on a shared border is covered by both neighbours; the
# ORDER BY makes that pick deterministic (lowest TERYT code) instead of planner-dependent.
# Holes (enclaves) are not covered by the surrounding gmina; outside every polygon
# (e.g. outside Poland) there is NO match - never a "nearest" fallback.
_RESOLVE_SQL = text(
    """
    SELECT id, teryt_code, slug, name
    FROM geo_areas
    WHERE boundary IS NOT NULL
      AND ST_Covers(boundary, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
    ORDER BY teryt_code, id
    LIMIT 1
    """
)


def resolve_gmina(db: Session, latitude: float, longitude: float) -> ResolvedArea | None:
    """lat/lon -> the gmina whose boundary covers the point, or None. PostgreSQL+PostGIS
    only. Never logs or stores the coordinates (ADR-002)."""
    row = db.execute(_RESOLVE_SQL, {"lat": latitude, "lon": longitude}).first()
    if row is None:
        return None
    return ResolvedArea(geo_area_id=row.id, teryt_code=row.teryt_code, slug=row.slug, name=row.name)
