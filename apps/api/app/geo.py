"""Deterministic geo matching (rule #9, never "na oko").

Two distinct methods, deliberately not mixed (BACKLOG TASK-6.2, ADR-019):
- `haversine_km`: nearest station/point (ADR-006) - for data geography.
- `resolve_gmina`: point-in-polygon - the ONLY method for administrative membership.
"""

import math
from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

EARTH_RADIUS_KM = 6371.0

# ADR-006/ADR-024: nearest-station match is only valid within this distance (inclusive).
# Beyond it the area has NO station ("brak danych dla obszaru") - never a "nearest" fallback.
MAX_MATCH_DISTANCE_KM = 50.0
METHOD_NEAREST_STATION = "nearest_station"


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
    """Pure, deterministic point -> stations (rule #9, ADR-024). `stations` are
    (station_id, lat, lon). Only stations within `max_km` (inclusive) qualify; result is
    sorted by distance rounded to 1 m, ties broken by station id (digit ids in numeric
    order), so input order never changes the outcome. Empty list = no data for the area."""
    scored = [
        (round(haversine_km(latitude, longitude, lat, lon), 3), sid) for sid, lat, lon in stations
    ]
    scored = [(km, sid) for km, sid in scored if km <= max_km]
    scored.sort(key=lambda t: (t[0], not t[1].isdigit(), len(t[1]), t[1]))
    return [StationMatch(sid, km) for km, sid in scored[:limit]]


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
